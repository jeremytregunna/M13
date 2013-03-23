#!/usr/bin/env python

import lldb
import commands
import optparse
import threading
import json
import bottle
from bottle import Bottle, route, run

app = Bottle()

@app.route('/info')
def info():
    return json.dumps({'version':lldb.debugger.GetVersionString()})

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
