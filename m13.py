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
    info = {
        'valid':       target.IsValid(),
        'debugger_id': target.GetDebugger().GetID(),
        'exe':         target.GetExecutable().GetFilename(),
        'exe_path':    target.GetExecutable().GetDirectory() + '/' + target.GetExecutable().GetFilename(),
        'breakpoints': breakpoints,
        'modules':     modules
    }
    return info

def info_for_target_at_index(idx):
    target = lldb.debugger.GetTargetAtIndex(idx)
    return info_for_target(target)

@app.get('/target/selected')
def selected_target_info():
    response.content_type = 'application/json; charset=utf8'
    target = lldb.debugger.GetSelectedTarget()
    return json.dumps(info_for_target(target))

@app.get('/target/info/:idx')
def target_info(idx):
    response.content_type = 'application/json; charset=utf8'
    return json.dumps(info_for_target(idx))

def m13(debugger, command, result, internal_dict):
    result.PrintCString("Unimplemented")

def thread_entry():
    app.run(host='localhost', port=8080, debug=False)

# And the initialization code to add your commands 
def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command script add -f m13.m13 m13')
    t = threading.Thread(target=thread_entry, args = ())
    t.daemon = True
    t.start()
    print 'The "m13" python command has been installed and is ready for use.\n'
