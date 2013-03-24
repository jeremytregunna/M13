#!/usr/bin/env python

import lldb
import commands
import optparse
import threading
import json
import bottle
from bottle import Bottle, route, run, request, response

app = Bottle()

def debugger_info(debugger):
    targets = []
    for target in debugger:
        targets.append(info_for_target(target))
    return {
        'id':          debugger.GetID(),    
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

def frame_info(frame):
    registers = []
    for r in frame.GetRegisters():
        registers.append(r.GetValue())
    return {
        'id': frame.GetFrameID(),
        'pc': frame.GetPC(),
        'sp': frame.GetSP(),
        'fp': frame.GetFP(),
        'function_name': frame.GetFunctionName(),
        'inlined':       frame.IsInlined(),
        'registers':     registers,
        'arguments':     [], #frame.get_arguments()
        'locals':        [], #frame.get_locals()
        'statics':       [], #frame.get_statics()
    }

def thread_info(thread):
    frames = []
    for f in thread.get_thread_frames():
        frames.append(frame_info(f))
    return {
        'id':         thread.GetThreadID(),
        'name':       thread.GetName(),
        'queue_name': thread.GetQueueName(),
        'frames':     frames
    }

def process_info_for_target(target):
    process = target.process
    threads = []
    for t in process.get_process_thread_list():
        threads.append(thread_info(t))
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

def m13(debugger, command, result, internal_dict):
    print 'm13 command does nothing currently.\n'

def thread_entry():
    app.run(host='localhost', port=8080, debug=False)

# And the initialization code to add your commands 
def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command script add -f m13.m13 m13')
    t = threading.Thread(target=thread_entry, args = ())
    t.daemon = True
    t.start()
    print 'The "m13" python command has been installed and is ready for use.\n'
