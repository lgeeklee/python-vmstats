#!/usr/bin/env python

"""
Python program that generates various statistics for one or more virtual machines

A list of virtual machines can be provided as a comma separated list.
"""

from __future__ import print_function
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl, vim
from datetime import timedelta, datetime

import argparse
import atexit
import getpass

import ssl

def GetArgs():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-s', '--host', required=True, action='store', help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store', help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, action='store', help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to host')
    parser.add_argument('-m', '--vm', required=True, action='store', help='On eor more Virtual Machines to report on')
    parser.add_argument('-c', '--cert_check_skip', required=False, action='store_true', help='skip ssl certificate check')
    parser.add_argument('-i', '--interval', type=int, default=15, action='store',
                        help='Interval to average the vSphere stats over')
    args = parser.parse_args()
    return args


def BuildQuery(content, vchtime, counterId, instance, vm, interval):
    perfManager = content.perfManager
    metricId = vim.PerformanceManager.MetricId(counterId=counterId, instance=instance)
    startTime = vchtime - timedelta(minutes=(interval + 1))
    endTime = vchtime - timedelta(minutes=1)
    query = vim.PerformanceManager.QuerySpec(intervalId=20, entity=vm, metricId=[metricId], startTime=startTime,
                                             endTime=endTime)
    perfResults = perfManager.QueryPerf(querySpec=[query])
    if perfResults:
        return perfResults
    else:
        print('ERROR: Performance results empty.  TIP: Check time drift on source and vCenter server')
        print('Troubleshooting info:')
        print('vCenter/host date and time: {}'.format(vchtime))
        print('Start perf counter time   :  {}'.format(startTime))
        print('End perf counter time     :  {}'.format(endTime))
        print(query)
        exit()



def PrintVmInfo(vm, content, vchtime, interval, perf_dict, ):
    statInt = interval * 3  # There are 3 20s samples in each minute
    summary = vm.summary
    disk_list = []
    network_list = []

    # Convert limit and reservation values from -1 to None
    if vm.resourceConfig.cpuAllocation.limit == -1:
        vmcpulimit = "None"
    else:
        vmcpulimit = "{} Mhz".format(vm.resourceConfig.cpuAllocation.limit)
    if vm.resourceConfig.memoryAllocation.limit == -1:
        vmmemlimit = "None"
    else:
        vmmemlimit = "{} MB".format(vm.resourceConfig.cpuAllocation.limit)

    if vm.resourceConfig.cpuAllocation.reservation == 0:
        vmcpures = "None"
    else:
        vmcpures = "{} Mhz".format(vm.resourceConfig.cpuAllocation.reservation)
    if vm.resourceConfig.memoryAllocation.reservation == 0:
        vmmemres = "None"
    else:
        vmmemres = "{} MB".format(vm.resourceConfig.memoryAllocation.reservation)

    vm_hardware = vm.config.hardware
    for each_vm_hardware in vm_hardware.device:
        if (each_vm_hardware.key >= 2000) and (each_vm_hardware.key < 3000):
            disk_list.append('{} | {:.1f}GB | Thin: {} | {}'.format(each_vm_hardware.deviceInfo.label,
                                                         each_vm_hardware.capacityInKB/1024/1024,
                                                         each_vm_hardware.backing.thinProvisioned,
                                                         each_vm_hardware.backing.fileName))
        elif (each_vm_hardware.key >= 4000) and (each_vm_hardware.key < 5000):
            network_list.append('{} | {} | {}'.format(each_vm_hardware.deviceInfo.label,
                                                         each_vm_hardware.deviceInfo.summary,
                                                         each_vm_hardware.macAddress))

    #CPU Ready Average
    statCpuReady = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'cpu.ready.summation')), "", vm, interval)
    cpuReady = (float(sum(statCpuReady[0].value[0].value)) / statInt)
    #CPU Usage Average % - NOTE: values are type LONG so needs divided by 100 for percentage
    statCpuUsage = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'cpu.usage.average')), "", vm, interval)
    cpuUsage = ((float(sum(statCpuUsage[0].value[0].value)) / statInt) / 100)
    #Memory Active Average MB
    statMemoryActive = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'mem.active.average')), "", vm, interval)
    memoryActive = (float(sum(statMemoryActive[0].value[0].value) / 1024) / statInt)
    #Memory Shared
    statMemoryShared = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'mem.shared.average')), "", vm, interval)
    memoryShared = (float(sum(statMemoryShared[0].value[0].value) / 1024) / statInt)
    #Memory Balloon
    statMemoryBalloon = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'mem.vmmemctl.average')), "", vm, interval)
    memoryBalloon = (float(sum(statMemoryBalloon[0].value[0].value) / 1024) / statInt)
    #Memory Swapped
    statMemorySwapped = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'mem.swapped.average')), "", vm, interval)
    memorySwapped = (float(sum(statMemorySwapped[0].value[0].value) / 1024) / statInt)
    #Datastore Average IO
    statDatastoreIoRead = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'datastore.numberReadAveraged.average')),
                                     "*", vm, interval)
    DatastoreIoRead = (float(sum(statDatastoreIoRead[0].value[0].value)) / statInt)
    statDatastoreIoWrite = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'datastore.numberWriteAveraged.average')),
                                      "*", vm, interval)
    DatastoreIoWrite = (float(sum(statDatastoreIoWrite[0].value[0].value)) / statInt)
    #Datastore Average Latency
    statDatastoreLatRead = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'datastore.totalReadLatency.average')),
                                      "*", vm, interval)
    DatastoreLatRead = (float(sum(statDatastoreLatRead[0].value[0].value)) / statInt)
    statDatastoreLatWrite = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'datastore.totalWriteLatency.average')),
                                       "*", vm, interval)
    DatastoreLatWrite = (float(sum(statDatastoreLatWrite[0].value[0].value)) / statInt)

    #Network usage (Tx/Rx)
    statNetworkTx = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'net.transmitted.average')), "", vm, interval)
    networkTx = (float(sum(statNetworkTx[0].value[0].value) * 8 / 1024) / statInt)
    statNetworkRx = BuildQuery(content, vchtime, (StatCheck(perf_dict, 'net.received.average')), "", vm, interval)
    networkRx = (float(sum(statNetworkRx[0].value[0].value) * 8 / 1024) / statInt)

    print('\nNOTE: Any VM statistics are averages of the last {} minutes\n'.format(statInt / 3))
    print('Server Name                    :', summary.config.name)
    print('Description                    :', summary.config.annotation)
    print('Guest                          :', summary.config.guestFullName)
    if vm.rootSnapshot:
        print('Snapshot Status                : Snapshots present')
    else:
        print('Snapshot Status                : No Snapshots')
    print('VM .vmx Path                   :', summary.config.vmPathName)
    try:
        print('Virtual Disks                  :', disk_list[0])
        if len(disk_list) > 1:
            disk_list.pop(0)
            for each_disk in disk_list:
                print('                                ', each_disk)
    except IndexError:
        pass
    print('Virtual NIC(s)                 :', network_list[0])
    if len(network_list) > 1:
        network_list.pop(0)
        for each_vnic in network_list:
            print('                                ', each_vnic)
    print('[VM] Limits                    : CPU: {}, Memory: {}'.format(vmcpulimit, vmmemlimit))
    print('[VM] Reservations              : CPU: {}, Memory: {}'.format(vmcpures, vmmemres))
    print('[VM] Number of vCPUs           :', summary.config.numCpu)
    print('[VM] CPU Ready                 : Average {:.1f} %, Maximum {:.1f} %'.format((cpuReady / 20000 * 100),
                                                                                       ((float(max(
                                                                                           statCpuReady[0].value[
                                                                                               0].value)) / 20000 * 100))))
    print('[VM] CPU (%)                   : {:.0f} %'.format(cpuUsage))
    print('[VM] Memory                    : {} MB ({:.1f} GB)'.format(summary.config.memorySizeMB, (float(summary.config.memorySizeMB) / 1024)))
    print('[VM] Memory Shared             : {:.0f} %, {:.0f} MB'.format(
        ((memoryShared / summary.config.memorySizeMB) * 100), memoryShared))
    print('[VM] Memory Balloon            : {:.0f} %, {:.0f} MB'.format(
        ((memoryBalloon / summary.config.memorySizeMB) * 100), memoryBalloon))
    print('[VM] Memory Swapped            : {:.0f} %, {:.0f} MB'.format(
        ((memorySwapped / summary.config.memorySizeMB) * 100), memorySwapped))
    print('[VM] Memory Active             : {:.0f} %, {:.0f} MB'.format(
        ((memoryActive / summary.config.memorySizeMB) * 100), memoryActive))
    print('[VM] Datastore Average IO      : Read: {:.0f} IOPS, Write: {:.0f} IOPS'.format(DatastoreIoRead,
                                                                                          DatastoreIoWrite))
    print('[VM] Datastore Average Latency : Read: {:.0f} ms, Write: {:.0f} ms'.format(DatastoreLatRead,
                                                                                      DatastoreLatWrite))
    print('[VM] Overall Network Usage     : Transmitted {:.3f} Mbps, Received {:.3f} Mbps'.format(networkTx, networkRx))
    print('[Host] Name                    : {}'.format(summary.runtime.host.name))
    print('[Host] CPU Detail              : Processor Sockets: {}, Cores per Socket {}'.format(
        summary.runtime.host.summary.hardware.numCpuPkgs,
        (summary.runtime.host.summary.hardware.numCpuCores / summary.runtime.host.summary.hardware.numCpuPkgs)))
    print('[Host] CPU Type                : {}'.format(summary.runtime.host.summary.hardware.cpuModel))
    print('[Host] CPU Usage               : Used: {} Mhz, Total: {} Mhz'.format(
        summary.runtime.host.summary.quickStats.overallCpuUsage,
        (summary.runtime.host.summary.hardware.cpuMhz * summary.runtime.host.summary.hardware.numCpuCores)))
    print('[Host] Memory Usage            : Used: {:.0f} GB, Total: {:.0f} GB\n'.format(
        (float(summary.runtime.host.summary.quickStats.overallMemoryUsage) / 1024),
        (float(summary.runtime.host.summary.hardware.memorySize) / 1024 / 1024 / 1024)))


def StatCheck(perf_dict, counter_name):
    counter_key = perf_dict[counter_name]
    return counter_key


def GetProperties(content, viewType, props, specType):
    # Build a view and get basic properties for all Virtual Machines
    objView = content.viewManager.CreateContainerView(content.rootFolder, viewType, True)
    tSpec = vim.PropertyCollector.TraversalSpec(name='tSpecName', path='view', skip=False, type=vim.view.ContainerView)
    pSpec = vim.PropertyCollector.PropertySpec(all=False, pathSet=props, type=specType)
    oSpec = vim.PropertyCollector.ObjectSpec(obj=objView, selectSet=[tSpec], skip=False)
    pfSpec = vim.PropertyCollector.FilterSpec(objectSet=[oSpec], propSet=[pSpec], reportMissingObjectsInResults=False)
    retOptions = vim.PropertyCollector.RetrieveOptions()
    totalProps = []
    retProps = content.propertyCollector.RetrievePropertiesEx(specSet=[pfSpec], options=retOptions)
    totalProps += retProps.objects
    while retProps.token:
        retProps = content.propertyCollector.ContinueRetrievePropertiesEx(token=retProps.token)
        totalProps += retProps.objects
    objView.Destroy()
    # Turn the output in retProps into a usable dictionary of values
    gpOutput = []
    for eachProp in totalProps:
        propDic = {}
        for prop in eachProp.propSet:
            propDic[prop.name] = prop.val
        propDic['moref'] = eachProp.obj
        gpOutput.append(propDic)
    return gpOutput


def main():
    args = GetArgs()
    try:
        vmnames = args.vm
        si = None
        if args.password:
            password = args.password
        else:
            password = getpass.getpass(prompt="Enter password for host {} and user {}: ".format(args.host, args.user))
        try:
            if args.cert_check_skip:
                context = ssl._create_unverified_context()
                si = SmartConnect(host=args.host,
                                  user=args.user,
                                  pwd=password,
                                  port=int(args.port),
                                  sslContext=context)
            else:
                si = SmartConnect(host=args.host,
                                  user=args.user,
                                  pwd=password,
                                  port=int(args.port))
        except IOError as e:
            pass
        if not si:
            print('Could not connect to the specified host using specified username and password')
            return -1

        atexit.register(Disconnect, si)
        content = si.RetrieveContent()
        # Get vCenter date and time for use as baseline when querying for counters
        vchtime = si.CurrentTime()

        # Get all the performance counters
        perf_dict = {}
        perfList = content.perfManager.perfCounter
        for counter in perfList:
            counter_full = "{}.{}.{}".format(counter.groupInfo.key, counter.nameInfo.key, counter.rollupType)
            perf_dict[counter_full] = counter.key

        retProps = GetProperties(content, [vim.VirtualMachine], ['name', 'runtime.powerState'], vim.VirtualMachine)

        #Find VM supplied as arg and use Managed Object Reference (moref) for the PrintVmInfo
        for vm in retProps:
            if (vm['name'] in vmnames) and (vm['runtime.powerState'] == "poweredOn"):
                PrintVmInfo(vm['moref'], content, vchtime, args.interval, perf_dict)
            elif vm['name'] in vmnames:
                print('ERROR: Problem connecting to Virtual Machine.  {} is likely powered off or suspended'.format(vm['name']))

    except vmodl.MethodFault as e:
        print('Caught vmodl fault : ' + e.msg)
        return -1
    except Exception as e:
        print('Caught exception : ' + str(e))
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
