# coding=UTF-8
'''
Created on 05.04.2013

@author: sysoev
'''
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import images

import datetime
import json
import loqc
import re

def force_unicode(string):
    if type(string) == unicode:
        return string
    return string.decode('utf-8')

class Project(db.Model):
    name = db.StringProperty(multiline = False)
    description = db.TextProperty()
    user = db.UserProperty(auto_current_user = True)
    created = db.DateTimeProperty(auto_now_add = True)
    updated = db.DateTimeProperty(auto_now = True)
    published = db.BooleanProperty(default = False)
    png = db.TextProperty() 

def getParentProject():
    proj = db.GqlQuery("SELECT * FROM Project WHERE name = :1", 'ParentOfAllProjects3717481125').fetch(1)
    if not proj:
        proj = Project(name="ParentOfAllProjects3717481125", description="This is not a project")
        proj.put()
        return proj
    else:
        return proj[0]

def getProjects():
    return db.GqlQuery("SELECT * FROM Project WHERE user = :1", users.get_current_user()).fetch(1000)
def getAllProjects():
    return db.GqlQuery("SELECT * FROM Project").fetch(10000)

def PublishProject(project_key, png):
    proj = Project.get(project_key)
    if proj.user != users.get_current_user():
        return 'Not authorized!'
    if proj.published:
        proj.published = False
        proj.put()
        return 'OK'
    if not GetCircuit(project_key):
        return 'Project is not ready. Simulate it first'
    proj.png = png
    proj.published = True
    proj.put()
    return 'OK'

def GetMatrices(project_key):
    proj = Project.get(project_key)
    if proj.user != users.get_current_user():
        return json.dumps('Not authorized!')
    circ = GetCircuit(project_key)
    if not circ:
        return json.dumps('Project is not ready. Simulate it first')
    if not circ.matrix or not circ.inv:
        return json.dumps('Project is not ready. Simulate it first')
    res = "Direct: " + circ.matrix.replace("[[", "\\( \\begin{pmatrix}").replace("]]", "\\end{pmatrix} \\)").replace("]&", "\\\\").replace("]", "\\\\").replace("[", "").replace("\n", " ")
    res_inv = "Inverse: " + circ.inv.replace("[[", "\\( \\begin{pmatrix}").replace("]]", "\\end{pmatrix} \\)").replace("]&", "\\\\").replace("]", "\\\\").replace("[", "").replace("\n", " ")
    
    regex = re.compile(r"[+-]0\.0+e\+00j", re.IGNORECASE)
    res = regex.sub("", res)
    res_inv = regex.sub("", res_inv)
    regex = re.compile(r"[+-]\d+\.\d+e-[123456789]\dj", re.IGNORECASE)
    res = regex.sub("", res)
    res_inv = regex.sub("", res_inv)
    regex = re.compile(r"\.0+e[+-]00", re.IGNORECASE)
    res = regex.sub("", res)
    res_inv = regex.sub("", res_inv)
    regex = re.compile(r"\d+\.\d+e-[123456789]\d", re.IGNORECASE)
    res = regex.sub("0", res)
    res_inv = regex.sub("0", res_inv)
    regex = re.compile(r"[+-]0\.j", re.IGNORECASE)
    res = regex.sub("", res)
    res_inv = regex.sub("", res_inv)
    return json.dumps("<br><br>" + res + "<br><br><br> " + res_inv + "<br><br>", default=str)

def CopyProject(project_key):
    try:
        proj = Project.get(project_key)
        if not proj.published:
            return 'You can\'t copy an un-published project!'
        parent_project = getParentProject()
        new_proj = Project(parent = parent_project.key())
        new_proj.name = 'Copy of ' + proj.name
        new_proj.description = proj.description
        new_proj.put()
    
        objects = db.GqlQuery("SELECT * FROM LODevice WHERE ANCESTOR is :1", proj).fetch(1000)
        for o in objects:
            new_device = LODevice(parent = new_proj.key())
            new_device.id = o.id
            new_device.type = o.type
            new_device.input_type = o.input_type
            new_device.theta = o.theta
            new_device.phi = o.phi
            new_device.n = o.n
            new_device.x = o.x
            new_device.y = o.y
            new_device.project_key = o.project_key
            new_device.put()
        conns = db.GqlQuery("SELECT * FROM LOConnection WHERE ANCESTOR is :1", proj).fetch(1000)
        for c in conns:
            new_conn = LOConnection(parent = new_proj.key())
            new_conn.line_json = c.line_json
            new_conn.put()
        return 'Project is copied!'
    except Exception as ex:
        return str(ex)    

def GetLibrary():
    projects = Project.all()
    projects.filter("published = ", True)
    res = [{'key': p.key(), 'name': p.name, 'descr': p.description, 'user': p.user} for p in projects]    
    return json.dumps(res, default=str)

'''
'     2022. Common methods 
'
'
'''
object_types = ['Project', 'LODevice', 'LOConnection', 'LOCircuit']

def CallCheck(project_key = None):
    user = users.get_current_user()
    if not user:
        return False
    if project_key:
        proj = Project.get(project_key)
        if proj.user != users.get_current_user():
            return False
    return True

def GetObjectByKey(object_type, key):
    try:
        if not CallCheck():
            return
        if object_type not in object_types:
            return
        gql_string = "SELECT * FROM " + object_type + " WHERE __key__ = KEY(:1) AND name != :2"
        objs = db.GqlQuery(gql_string, key, "ParentOfAllProjects3717481125").fetch(1)
        if objs:
            return json.dumps(objs[0]._entity, default=str)
        else:
            return json.dumps({})
    except Exception as ex:
        return str(ex)

def CycleObjects(object_type, parent_key):
    try:
        if not CallCheck():
            return
        if object_type not in object_types:
            return
        if parent_key == "current_user":
            parent_key = users.get_current_user()
            parent_project = getParentProject()
            gql_string = "SELECT * FROM " + object_type + " WHERE user = :1 AND ANCESTOR is :2 AND name != :3"
            objs = db.GqlQuery(gql_string, parent_key, parent_project.key(), "ParentOfAllProjects3717481125").fetch(1000)
        else:
            gql_string = "SELECT * FROM " + object_type + " WHERE ANCESTOR is :1"
            objs = db.GqlQuery(gql_string, parent_key).fetch(1000)
        if objs:
            return json.dumps([[str(e.key()), e._entity] for e in objs], default=str)
        else:
            return json.dumps([])
    except Exception as ex:
        return str(ex)

def DeleteCycleObject(key, object_type):
    try:
        if not CallCheck():
            return
        if object_type not in object_types:
            return
        gql_string = "SELECT * FROM " + object_type + " WHERE __key__ = KEY(:1) AND name != :2"
        objs = db.GqlQuery(gql_string, key, "ParentOfAllProjects3717481125").fetch(1)
        objs[0].delete()
        return 'OK'
    except Exception as ex:
        return str(ex)

def AddCycleObject(data, object_type, parent_key):
    try:
        if not CallCheck():
            return
        if object_type not in object_types:
            return
        obj = json.loads(data)
        dataClass = globals()[object_type]
        if parent_key == "current_user":
            parent_project = getParentProject()
            instance = dataClass(parent = parent_project.key())
        else:
            # check rights
            proj = Project.get(parent_key)
            if proj.user != users.get_current_user():
                return 'Not authorized'
            instance = dataClass(parent = db.Key(parent_key))
        for key in obj:
            setattr(instance, key, obj[key])
        instance.put()
        return 'OK'
    except Exception as ex:
        return str(ex)

# It is used only for projects! Hence the security check
def EditCycleObject(key, data, object_type):
    try:
        if not CallCheck():
            return
        # check rights
        proj = Project.get(key)
        if proj.user != users.get_current_user():
            return 'Not authorized'            
        if object_type not in object_types:
            return
        obj = json.loads(data)
        dataClass = globals()[object_type]
        instance = dataClass.get(key)
        if getattr(instance, "name") == "ParentOfAllProjects3717481125":
            return 'Wrong key'
        for k in obj:
            setattr(instance, k, obj[k])
        instance.put()
        return 'OK'
    except Exception as ex:
        return str(ex)
        
'''
'     LOQC Data 
'
'
'''
class LODevice(db.Model):
    id = db.StringProperty(multiline = False)
    type = db.StringProperty(multiline = False)
    theta = db.StringProperty(multiline = False)
    phi = db.StringProperty(multiline = False)
    n = db.StringProperty(multiline = False)
    input_type = db.StringProperty(multiline = False, default = "0")
    x = db.IntegerProperty(default = 100)
    y = db.IntegerProperty(default = 100)
    project_key = db.StringProperty(multiline = False) 
class LOConnection(db.Model):
    line_json = db.TextProperty()
class LOCircuit(db.Model):
    name = db.StringProperty(multiline = False)
    modes = db.IntegerProperty()
    matrix = db.TextProperty()
    inv = db.TextProperty()
    result = db.TextProperty()
    fidelities = db.TextProperty()
    cgate_run_x = db.TextProperty()
    cgate_run_y = db.TextProperty()
    cgate_run_z = db.TextProperty()

def ClearProjectDesign(key):
    try:
        proj = Project.get(key)
        if not proj:
            return "No project"
        if proj.user != users.get_current_user():
            return "Not authorized"
        objects = db.GqlQuery("SELECT * FROM LODevice WHERE ANCESTOR is :1", proj).fetch(1000)
        for o in objects:
            o.delete()
        conns = db.GqlQuery("SELECT * FROM LOConnection WHERE ANCESTOR is :1", proj).fetch(1000)
        for c in conns:
            c.delete()
        circuit = db.GqlQuery("SELECT * FROM LOCircuit WHERE ANCESTOR is :1", proj).fetch(1000)
        for c in circuit:
            c.delete()            
        return "OK"
    except Exception as ex:
        return str(ex)

def ProcessConns(conns, devices):
    devs = [{"id": d.id, "type": d.type, "theta": d.theta, "phi": d.phi, "n": d.n, "input_type": d.input_type, "x": d.x, "y": d.y, 
            "inputs": [], "outputs": [], "step": -1, "modes": [], "project_key": d.project_key} for d in devices]
    for c in conns:
        con = json.loads(c.line_json)
        source_node = con[0]['source']['node']
        source_port = con[0]['source']['port']
        target_node = con[0]['target']['node']
        target_port = con[0]['target']['port']
        for d in devs:
            if d['id'] == source_node:
                source_dev = d
            if d['id'] == target_node:
                target_dev = d
        if (not source_dev) or not (target_dev):
            return None
        if source_dev['type'] == "OUT" or target_dev['type'] == "IN":
            source_node = con[0]['target']['node']
            source_port = con[0]['target']['port']
            target_node = con[0]['source']['node']
            target_port = con[0]['source']['port']
            tmp = source_dev
            source_dev = target_dev
            target_dev = tmp
        elif source_dev['type'] == "IN" or target_dev['type'] == "OUT":
            pass
        elif source_port in ["hybrid" + str(2*i) for i in range(50)]:
            source_node = con[0]['target']['node']
            source_port = con[0]['target']['port']
            target_node = con[0]['source']['node']
            target_port = con[0]['source']['port']
            tmp = source_dev
            source_dev = target_dev
            target_dev = tmp  
        source_dev['outputs'].append(target_node)
        target_dev['inputs'].append(source_node)
        target_dev['modes'].append({'my_port': target_port, 'source': source_node, 'source_port': source_port, 'mode': -1})
    return devs

def ProcessDevStep(d, devs, processed_devs):
    if d['step'] >= 0:
        return d['step']
    if d['id'] in processed_devs:
        return -1
    processed_devs.append(d['id'])
    if len(d['inputs']) == 0:
        d['step'] = 0
        return 0
    cur_step = -1    
    for input in d['inputs']:
        for d1 in devs:
            if d1['id'] == input:
                if d1['step'] > 0:
                    cur_step = max(d1['step'] + 1, cur_step)
                else:
                    cur_step = max(ProcessDevStep(d1, devs, processed_devs) + 1, cur_step)
                break
    d['step'] = cur_step
    return cur_step

def ProcessSteps(devs):
    devs_sorted = sorted(devs, key=lambda d: d['x'])
    processed_devs = []
    for d in devs_sorted:
        ProcessDevStep(d, devs, processed_devs)

def ProcessDevMode(dev, devs, processed_devs):
    # check for recursive definitions
    if dev['id'] in processed_devs:
        return
    processed_devs.append(dev['id'])
    
    # iterate all modes in device
    for mode in dev['modes']:
        # if the mode not yet assigned
        if mode['mode'] < 0:
            # find source
            source = None
            for d in devs:
                if d['id'] == mode['source']:
                    source = d
                    break
            if not source:
                return

            # find source mode
            source_mode = None
            for m in source['modes']:
                # this is dirty, fix later
                source_port = m['my_port']
                if source['type'] == "User Project":
                    for i in range(0, 50, 2):
                        source_port = source_port.replace(str(i), str(i+1))
                if source['type'] == "BS":
                    source_port = source_port.replace("2", "3")
                    source_port = source_port.replace("0", "1")
                if source['type'] == "PS":
                    source_port = source_port.replace("0", "1")
                if mode['source_port'] == source_port:
                    source_mode = m
                    break
            if not source_mode:
                return

            # recursive call
            if source_mode['mode'] < 0:
                ProcessDevMode(source, devs, processed_devs)
            mode['mode'] = source_mode['mode']
            
def GetCircuit(project_key):
    try:
        proj = Project.get(project_key)
        if not proj:
            return None
        circuit = db.GqlQuery("SELECT * FROM LOCircuit WHERE ANCESTOR is :1", proj).fetch(1)
        if not circuit:
            return None
        if len(circuit) == 0:
            return None
        return circuit[0]            
    except Exception as ex:
        return None            

def ProcessModes(devs):
    # sort inputs from top to bottom
    inputs = [a for a in devs if a['type'] == "IN"]
    ins = sorted(inputs, key=lambda d: d['y']) 

    # assign modes to inputs
    processed_devs = []
    mode = 0
    for i in ins:
        i['modes'] = [{'my_port': 'hybrid0', 'source': None, 'mode': mode}]
        processed_devs.append(i['id'])
        mode += 1

    # sort devs from left to right
    sorted_devs = sorted(devs, key=lambda d: d['x']) 

    # process dev modes
    for d in sorted_devs:
        ProcessDevMode(d, devs, processed_devs)

    # check if everything is correctly defined
    for d in devs:
        if d['type'] == "IN" and len(d['modes']) != 1:
            return 0
        if d['type'] == "OUT" and len(d['modes']) != 1:
            return 0
        if d['type'] == "BS" and len(d['modes']) != 2:
            return 0
        if d['type'] == "PS" and len(d['modes']) != 1:
            return 0
        if d['type'] == "User Project":
            circ = GetCircuit(d['project_key'])
            if not circ:
                return 0
            if circ.modes != len(d['modes']):
                return 0            

        for m in d['modes']:
            if m['mode'] < 0:
                return 0

    # check passed!
    return len(ins)

def getDevsModes(proj):
    try:
        devices = db.GqlQuery("SELECT * FROM LODevice WHERE ANCESTOR is :1", proj).fetch(1000)
        conns = db.GqlQuery("SELECT * FROM LOConnection WHERE ANCESTOR is :1", proj).fetch(1000)

        devs = ProcessConns(conns, devices)
        if not devs:
            return None, None, json.dumps("The circuit didn't pass the completeness check! It might lack inputs/outputs or it is recursive")
        ProcessSteps(devs)
        modes = ProcessModes(devs) 
        if modes == 0:
            return None, None, json.dumps("The circuit didn't pass the completeness check! It might lack inputs/outputs or it is recursive")
        return devs, modes, ""
    except Exception as ex:
        return None, None, str(ex)

def ConstructCircuit(project_key):
    try:
        proj = Project.get(project_key)
        if not proj:
            return "No project"
        if proj.user != users.get_current_user():
            return "Not authorized"

        # check if we already did the calculation
        circuit = db.GqlQuery("SELECT * FROM LOCircuit WHERE ANCESTOR is :1", proj).fetch(1)
        if circuit:
            return json.dumps(circuit[0].result, default=str)

        # prepare circuit
        devs, modes, error = getDevsModes(proj)
        if error:
            return error

        # run circuit
        lx, matrix, inv = loqc.ConstructCircuit(devs, modes)

        # splitting
        terms_p = lx.split("+")
        res = ""
        for t in terms_p:
            terms_m = t.split("-")
            res_m = ""
            if len(terms_m) <= 1:
                res_m = "\\(" + t + "\\)" + "-"
            else:
                for t1 in terms_m:
                    res_m += "\\(" + t1 + "\\)" + "-"
            res += res_m[:-1] + "+"

        # save result
        circ = LOCircuit(parent = proj.key())
        circ.modes = modes
        circ.matrix = matrix
        circ.inv = inv
        circ.result = res[:-1]
        #cgate_res, error = loqc.get_cgate_run(project_key)
        #if not error:
        #    circ.result += cgate_res
        circ.name = proj.name
        circ.put()
        
        return json.dumps(circ.result, default=str)
    except Exception as ex:
        return str(ex)

