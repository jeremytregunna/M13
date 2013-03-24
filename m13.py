#!/usr/bin/env python

import lldb
import commands
import optparse
import threading
import json
import select
import pybonjour
import bottle
from bottle import Bottle, route, run, request, response

app = Bottle()

def get_registers(frame, kind):
    '''Returns the registers given the frame and the kind of registers desired.
    Returns None if there's no such kind.
    '''
    registerSet = frame.GetRegisters() # Return type of SBValueList.
    for value in registerSet:
        if kind.lower() in value.GetName().lower():
            return value
    return None

def debugger_info(debugger):
    targets = []
    for target in debugger:
        targets.append(info_for_target(target))
    return {
        'id':          hex(debugger.GetID()),
        'version':     debugger.GetVersionString(),
        'name':        debugger.GetInstanceName(),
        'prompt':      debugger.GetPrompt(),
        'valid':       debugger.IsValid(),
        'async':       debugger.GetAsync(),
        'targets':     targets
    }

@app.get('/debugger')
def info():
    response.content_type = 'application/json; charset=utf8'
    return json.dumps(debugger_info(lldb.debugger))

@app.get('/debugger/:debugger_id')
def debugger_with_id(debugger_id):
    response.content_type = 'application/json; charset=utf8'
    debugger = lldb.debugger.FindDebuggerWithID(int(debugger_id))
    return json.dumps(debugger_info(debugger))

@app.put('/debugger/prompt')
def set_prompt():
    response.content_type = 'application/json; charset=utf8'
    prompt = request.forms.get('prompt')
    lldb.debugger.SetPrompt(prompt)
    return json.dumps(debugger_info(lldb.debugger))

@app.put('/debugger/async')
def set_async():
    response.content_type = 'application/json; charset=utf8'
    lldb.debugger.SetAsync(not lldb.debugger.GetAsync())
    return json.dumps(debugger_info(lldb.debugger))

def info_for_target(target):
    breakpoints = []
    for b in target.breakpoint_iter():
        breakpoints.append(b.GetID())
    modules = []
    for m in target.module_iter():
        modules.append(m.GetUUIDString())
    return {
        'valid':       target.IsValid(),
        'debugger_id': target.GetDebugger().GetID(),
        'exe':         target.GetExecutable().GetFilename(),
        'exe_path':    target.GetExecutable().GetDirectory() + '/' + target.GetExecutable().GetFilename(),
        'breakpoints': breakpoints,
        'modules':     modules
    }

def info_for_target_at_index(idx):
    target = lldb.debugger.GetTargetAtIndex(idx)
    return info_for_target(target)

@app.get('/target/:idx')
def target_info(idx):
    response.content_type = 'application/json; charset=utf8'
    if idx == 'selected':
        return json.dumps(info_for_target(lldb.debugger.GetSelectedTarget()))
    else:
        return json.dumps(info_for_target_at_index(int(idx)))

def breakpoint_info(breakpoint):
    return {
        'id': breakpoint.GetID(),
        'valid': breakpoint.IsValid(),
        'enabled': breakpoint.IsEnabled(),
        'one_shot': breakpoint.IsOneShot(),
        'internal': breakpoint.IsInternal(),
        'hit_count': breakpoint.GetHitCount(),
        'condition': breakpoint.GetCondition(),
        'thread_id': hex(breakpoint.GetThreadID())
    }

def breakpoint_for_id(target, breakpoint_id):
    for b in target.breakpoint_iter():
        if b.GetID() == int(breakpoint_id):
            return b
    return None

@app.get('/target/:idx/breakpoints')
def target_breakpoint_info(idx):
    response.content_type = 'application/json; charset=utf8'
    target = target_for_idx(idx)
    breakpoints = []
    for b in target.breakpoint_iter():
        breakpoints.append(breakpoint_info(b))
    return json.dumps({'breakpoints': breakpoints})

@app.put('/target/:idx/breakpoints/:breakpoint_id/enable')
def breakpoint_enable(idx, breakpoint_id):
    response.content_type = 'application/json; charset=utf8'
    target = target_for_idx(idx)
    breakpoint = breakpoint_for_id(target, breakpoint_id)
    if breakpoint:
        breakpoint.SetEnabled(not breakpoint.IsEnabled())
        return json.dumps(breakpoint_info(breakpoint))
    else:
        return json.dumps({'error':{'message':'Unable to find breakpoint.'}})

def frame_info(frame):
    registers = []
    regs = get_registers(frame, 'general purpose')
    for reg in regs:
        registers.append({reg.GetName(): reg.GetValue()})
    arguments = []
    for arg in frame.get_arguments():
        arguments.append({arg.GetName(): arg.GetValue()})
    local_variables = []
    for local in frame.get_locals():
        local_variables.append({local.GetName(): local.GetValue()})
    statics = []
    for s in frame.get_statics():
        statics.append({s.GetName(): s.GetValue()})
    return {
        'id': frame.GetFrameID(),
        'pc': frame.GetPC(),
        'sp': frame.GetSP(),
        'fp': frame.GetFP(),
        'function_name': frame.GetFunctionName(),
        'inlined':       frame.IsInlined(),
        'registers':     registers,
        'arguments':     arguments,
        'locals':        local_variables,
        'statics':       statics
    }

def thread_info(thread):
    frames = []
    for f in thread.get_thread_frames():
        frames.append(frame_info(f))
    return {
        'id':         thread.GetThreadID(),
        'name':       thread.GetName(),
        'queue_name': thread.GetQueueName(),
        'frames':     frames,
        'suspended':  thread.IsSuspended()
    }

def thread_for_id(target, thread_id):
    for t in target.process.get_process_thread_list():
        if t.GetThreadID() == thread_id:
            return t
    return None

def process_info_for_target(target):
    process = target.process
    threads = []
    for t in process.get_process_thread_list():
        threads.append(t.GetThreadID())
    return {
        'id':        process.GetProcessID(),
        'state':     process.GetState(),
        'byteorder': process.GetByteOrder(),
        'threads':   threads
    }

def target_for_idx(idx):
    if idx == 'selected':
        target = lldb.debugger.GetSelectedTarget()
    else:
        target = lldb.debugger.GetTargetAtIndex(int(idx))
    return target

@app.get('/target/:idx/process')
def process_info(idx):
    response.content_type = 'application/json; charset=utf8'
    target = target_for_idx(idx)
    return json.dumps(process_info_for_target(target))

@app.get('/target/:idx/process/:action')
def process_action(idx, action):
    response.content_type = 'application/json; charset=utf8'
    target = target_for_idx(idx)
    process = target.process
    if action == 'continue':
        process.Continue()
    elif action == 'stop':
        process.Stop()
    elif action == 'kill':
        process.Kill()
    elif action == 'detach':
        process.Detach()
    else:
        return json.dumps({'error':{'message': 'Unknown action.'}})
    return json.dumps(process_info_for_target(target))

@app.get('/target/:idx/thread/:thread_id')
def target_thread_info(idx, thread_id):
    response.content_type = 'application/json; charset=utf8'
    target = target_for_idx(idx)
    thread = thread_for_id(target, int(thread_id))
    return json.dumps(thread_info(thread))

def step_function_name(action):
    return {
        'step_over': 'StepOver',
        'step_into': 'StepInto',
        'step_out':  'StepOut',
        'suspend':   'Suspend',
        'resume':    'Resume'
    }.get(action, None)

@app.get('/target/:idx/thread/:thread_id/:step_action')
def thread_step_over(idx, thread_id, step_action):
    response.content_type = 'application/json; charset=utf8'
    target = target_for_idx(idx)
    thread = thread_for_id(target, int(thread_id))
    if thread:
        function_name = step_function_name(step_action)
        function = getattr(thread, function_name)
        function()
        return json.dumps(thread_info(thread))
    else:
        return json.dumps({'error':{'message':'Unable to step over instruction.'}})

def m13(debugger, command, result, internal_dict):
    print 'm13 command does nothing currently.\n'

def entry():
    port = 8080
    sdRef = pybonjour.DNSServiceRegister(name = 'M13', regtype = '_m13._tcp', port = port)
    ready = select.select([sdRef], [], [])
    if sdRef in ready[0]:
        pybonjour.DNSServiceProcessResult(sdRef)
    app.run(host = 'localhost', port = port, debug = False)

# And the initialization code to add your commands 
def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command script add -f m13.m13 m13')
    t = threading.Thread(target=entry, args = ())
    t.daemon = True
    t.start()
    print 'The "m13" python command has been installed and is ready for use.\n'
