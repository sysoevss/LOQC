# coding=UTF-8
'''
Created on 05.04.2013

@author: sysoev
'''
from contextlib import contextmanager
import datetime
import json
import math
import re
import functools

import users_compat as users
from google.cloud import ndb

import loqc
import owqc

def force_unicode(value):
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode('utf-8')
    return str(value)


def current_user_email():
    user = users.get_current_user()
    if not user:
        return None
    if hasattr(user, "email") and callable(user.email):
        return user.email()
    return force_unicode(user)


def normalize_user_value(value):
    if not value:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if hasattr(value, "email") and callable(value.email):
        return value.email()
    if isinstance(value, dict):
        email = value.get("email") or value.get("Email")
        if email:
            return force_unicode(email)
    return None


ndb_client = ndb.Client()


@contextmanager
def ndb_context():
    try:
        ndb.get_context()
    except Exception:
        with ndb_client.context():
            yield
    else:
        yield


def with_ndb_context(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with ndb_context():
            return func(*args, **kwargs)
    return wrapper


_LEGACY_KEY_TOKEN = re.compile(
    r"(u?'[^']*'|u?\"[^\"]*\"|-?\d+)"
)


def _parse_legacy_key_string(value):
    if not value or not value.startswith("Key(") or not value.endswith(")"):
        return None
    inner = value[4:-1].strip()
    if not inner:
        return None
    tokens = []
    for match in _LEGACY_KEY_TOKEN.finditer(inner):
        token = match.group(0)
        if token.startswith(("u'", 'u"')):
            token = token[1:]
        if token.startswith(("'", '"')) and token.endswith(("'", '"')):
            tokens.append(token[1:-1])
        else:
            try:
                tokens.append(int(token))
            except ValueError:
                return None
    if len(tokens) < 2 or len(tokens) % 2 != 0:
        return None
    try:
        return ndb.Key(*tokens)
    except Exception:
        return None


def key_from_str(key_str):
    if isinstance(key_str, ndb.Key):
        return key_str
    if key_str is None:
        return None
    value = force_unicode(key_str).strip()
    if not value:
        return None
    try:
        return ndb.Key(urlsafe=value)
    except Exception:
        return _parse_legacy_key_string(value)


def key_to_str(key):
    if not key:
        return ""
    return key.urlsafe().decode("utf-8")

class BaseModel(ndb.Model):
    @classmethod
    def get(cls, key):
        key_obj = key_from_str(key)
        if not key_obj:
            return None
        return key_obj.get()


class Project(BaseModel):
    name = ndb.StringProperty()
    description = ndb.TextProperty()
    user = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    published = ndb.BooleanProperty(default=False)
    png = ndb.TextProperty()

@with_ndb_context
def getParentProject():
    proj = Project.query(Project.name == 'ParentOfAllProjects3717481125').fetch(1)
    if not proj:
        proj = Project(name="ParentOfAllProjects3717481125", description="This is not a project")
        proj.put()
        return proj
    return proj[0]

@with_ndb_context
def getProjects():
    user_email = current_user_email()
    if not user_email:
        return []
    return Project.query(Project.user == user_email).fetch(1000)


@with_ndb_context
def getAllProjects():
    return Project.query().fetch(10000)

@with_ndb_context
def PublishProject(project_key, png):
    proj = Project.get(project_key)
    if not proj:
        return 'No project'
    if proj.user != current_user_email():
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

@with_ndb_context
def GetMatrices(project_key):
    proj = Project.get(project_key)
    if not proj:
        return json.dumps('No project')
    if proj.user != current_user_email():
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

@with_ndb_context
def CopyProject(project_key):
    try:
        proj = Project.get(project_key)
        if not proj:
            return 'No project'
        if not proj.published:
            return 'You can\'t copy an un-published project!'
        parent_project = getParentProject()
        new_proj = Project(parent=parent_project.key)
        new_proj.name = 'Copy of ' + proj.name
        new_proj.description = proj.description
        new_proj.user = current_user_email()
        new_proj.put()

        objects = LODevice.query(ancestor=proj.key).fetch(1000)
        for o in objects:
            new_device = LODevice(parent=new_proj.key)
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
        conns = LOConnection.query(ancestor=proj.key).fetch(1000)
        for c in conns:
            new_conn = LOConnection(parent=new_proj.key)
            new_conn.line_json = c.line_json
            new_conn.put()
        ow_objects = OWDevice.query(ancestor=proj.key).fetch(1000)
        for o in ow_objects:
            new_device = OWDevice(parent=new_proj.key)
            new_device.id = o.id
            new_device.type = o.type
            new_device.index = o.index
            new_device.angle = o.angle
            new_device.result = o.result
            new_device.x = o.x
            new_device.y = o.y
            new_device.put()
        ow_conns = OWConnection.query(ancestor=proj.key).fetch(1000)
        for c in ow_conns:
            new_conn = OWConnection(parent=new_proj.key)
            new_conn.line_json = c.line_json
            new_conn.put()
        return 'Project is copied!'
    except Exception as ex:
        return str(ex)

@with_ndb_context
def GetLibrary():
    projects = Project.query(Project.published == True).fetch()
    res = [{'key': key_to_str(p.key), 'name': p.name, 'descr': p.description, 'user': p.user} for p in projects]
    return json.dumps(res, default=str)

'''
'     2022. Common methods 
'
'
'''
object_types = ['Project', 'LODevice', 'LOConnection', 'LOCircuit', 'OWDevice', 'OWConnection']

@with_ndb_context
def CallCheck(project_key=None):
    user_email = current_user_email()
    if not user_email:
        return False
    if project_key:
        proj = Project.get(project_key)
        if not proj:
            return False
        if proj.user != user_email:
            return False
    return True

@with_ndb_context
def GetObjectByKey(object_type, key):
    try:
        if not CallCheck():
            return
        if object_type not in object_types:
            return
        data_class = globals()[object_type]
        obj = data_class.get(key)
        if obj and getattr(obj, "name", None) != "ParentOfAllProjects3717481125":
            return json.dumps(obj.to_dict(), default=str)
        return json.dumps({})
    except Exception as ex:
        return str(ex)

@with_ndb_context
def CycleObjects(object_type, parent_key):
    try:
        if not CallCheck():
            return
        if object_type not in object_types:
            return
        data_class = globals()[object_type]
        if parent_key == "current_user":
            parent_key = current_user_email()
            if not parent_key:
                return json.dumps([])
            parent_project = getParentProject()
            objs = data_class.query(
                data_class.user == parent_key,
                ancestor=parent_project.key
            ).fetch(1000)
            objs = [o for o in objs if getattr(o, "name", None) != "ParentOfAllProjects3717481125"]
        else:
            ancestor_key = key_from_str(parent_key)
            if not ancestor_key:
                return json.dumps([])
            objs = data_class.query(ancestor=ancestor_key).fetch(1000)
        if objs:
            return json.dumps([[key_to_str(e.key), e.to_dict()] for e in objs], default=str)
        return json.dumps([])
    except Exception as ex:
        return str(ex)

@with_ndb_context
def DeleteCycleObject(key, object_type):
    try:
        if not CallCheck():
            return
        if object_type not in object_types:
            return
        data_class = globals()[object_type]
        obj = data_class.get(key)
        if obj and getattr(obj, "name", None) != "ParentOfAllProjects3717481125":
            obj.key.delete()
        return 'OK'
    except Exception as ex:
        return str(ex)

@with_ndb_context
def AddCycleObject(data, object_type, parent_key):
    try:
        if not CallCheck():
            return
        if object_type not in object_types:
            return
        obj = json.loads(data)
        data_class = globals()[object_type]
        if parent_key == "current_user":
            parent_project = getParentProject()
            instance = data_class(parent=parent_project.key)
        else:
            # check rights
            proj = Project.get(parent_key)
            if not proj:
                return 'No project'
            if proj.user != current_user_email():
                return 'Not authorized'
            instance = data_class(parent=key_from_str(parent_key))
        for key in obj:
            setattr(instance, key, obj[key])
        if object_type == "Project" and not getattr(instance, "user", None):
            instance.user = current_user_email()
        instance.put()
        return 'OK'
    except Exception as ex:
        return str(ex)

# It is used only for projects! Hence the security check
@with_ndb_context
def EditCycleObject(key, data, object_type):
    try:
        if not CallCheck():
            return
        # check rights
        proj = Project.get(key)
        if proj.user != current_user_email():
            return 'Not authorized'
        if object_type not in object_types:
            return
        obj = json.loads(data)
        data_class = globals()[object_type]
        instance = data_class.get(key)
        if getattr(instance, "name") == "ParentOfAllProjects3717481125":
            return 'Wrong key'
        for k in obj:
            setattr(instance, k, obj[k])
        instance.put()
        return 'OK'
    except Exception as ex:
        return str(ex)


@with_ndb_context
def MigrateProjectUsers(fallback_email=None, limit=1000):
    try:
        projects = Project.query().fetch(limit)
        updated = 0
        skipped = 0
        for proj in projects:
            normalized = normalize_user_value(proj.user)
            if not normalized and fallback_email:
                normalized = fallback_email
            if not normalized:
                skipped += 1
                continue
            if proj.user != normalized:
                proj.user = normalized
                proj.put()
                updated += 1
        return json.dumps({"updated": updated, "skipped": skipped, "total": len(projects)}, default=str)
    except Exception as ex:
        return json.dumps({"error": True, "data": str(ex)}, default=str)
        
'''
'     LOQC Data 
'
'
'''
class LODevice(BaseModel):
    id = ndb.StringProperty()
    type = ndb.StringProperty()
    theta = ndb.StringProperty()
    phi = ndb.StringProperty()
    n = ndb.StringProperty()
    input_type = ndb.StringProperty(default="0")
    x = ndb.IntegerProperty(default=100)
    y = ndb.IntegerProperty(default=100)
    project_key = ndb.StringProperty()


class LOConnection(BaseModel):
    line_json = ndb.TextProperty()


class OWDevice(BaseModel):
    id = ndb.StringProperty()
    type = ndb.StringProperty()
    index = ndb.StringProperty()
    angle = ndb.StringProperty()
    result = ndb.StringProperty()
    x = ndb.IntegerProperty(default=100)
    y = ndb.IntegerProperty(default=100)


class OWConnection(BaseModel):
    line_json = ndb.TextProperty()


class LOCircuit(BaseModel):
    name = ndb.StringProperty()
    modes = ndb.IntegerProperty()
    matrix = ndb.TextProperty()
    inv = ndb.TextProperty()
    result = ndb.TextProperty()
    fidelities = ndb.TextProperty()
    cgate_run_x = ndb.TextProperty()
    cgate_run_y = ndb.TextProperty()
    cgate_run_z = ndb.TextProperty()

@with_ndb_context
def ClearProjectDesign(key):
    try:
        proj = Project.get(key)
        if not proj:
            return "No project"
        if proj.user != current_user_email():
            return "Not authorized"
        objects = LODevice.query(ancestor=proj.key).fetch(1000)
        for o in objects:
            o.key.delete()
        conns = LOConnection.query(ancestor=proj.key).fetch(1000)
        for c in conns:
            c.key.delete()
        circuit = LOCircuit.query(ancestor=proj.key).fetch(1000)
        for c in circuit:
            c.key.delete()
        return "OK"
    except Exception as ex:
        return str(ex)

@with_ndb_context
def ClearOWDesign(key):
    try:
        proj = Project.get(key)
        if not proj:
            return "No project"
        if proj.user != current_user_email():
            return "Not authorized"
        objects = OWDevice.query(ancestor=proj.key).fetch(1000)
        for o in objects:
            o.key.delete()
        conns = OWConnection.query(ancestor=proj.key).fetch(1000)
        for c in conns:
            c.key.delete()
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
        source_dev = None
        target_dev = None
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
            
@with_ndb_context
def GetCircuit(project_key):
    try:
        proj = Project.get(project_key)
        if not proj:
            return None
        circuit = LOCircuit.query(ancestor=proj.key).fetch(1)
        if not circuit:
            return None
        if len(circuit) == 0:
            return None
        return circuit[0]
    except Exception:
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

@with_ndb_context
def getDevsModes(proj):
    try:
        devices = LODevice.query(ancestor=proj.key).fetch(1000)
        conns = LOConnection.query(ancestor=proj.key).fetch(1000)

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

def _parse_ow_device_index(device):
    raw = device.index
    if raw is None or raw == "" or str(raw) == "-1":
        return None
    return int(raw)


def _ow_angle_specified(device):
    return device.angle is not None and str(device.angle).strip() != ""


def _ow_result_specified(device):
    return str(device.result).strip() in ("0", "1")


def _ow_simulation_node_index(device, n_q):
    """Q nodes use designer index; IN nodes use Hilbert-space index after entanglement."""
    idx = _parse_ow_device_index(device)
    if device.type == "IN":
        return n_q + idx
    return idx


def _build_ow_simulation_inputs(devices, conns):
    by_id = {d.id: d for d in devices}
    graph = []
    seen_edges = set()
    for c in conns:
        con = json.loads(c.line_json)
        src_id = con[0]["source"]["node"]
        tgt_id = con[0]["target"]["node"]
        src = by_id.get(src_id)
        tgt = by_id.get(tgt_id)
        if not src or not tgt:
            continue
        if src.type != "Q" or tgt.type != "Q":
            continue
        i = _parse_ow_device_index(src)
        j = _parse_ow_device_index(tgt)
        if i is None or j is None:
            return None, "Each Q node in a connection must have a valid index."
        edge = (min(i, j), max(i, j))
        if edge not in seen_edges:
            seen_edges.add(edge)
            graph.append([edge[0], edge[1]])

    n_q = 0
    if graph:
        n_q = max(max(edge) for edge in graph)

    ins = []
    observables = []
    results = []
    in_indices_seen = set()
    q_indices_seen = set()
    for d in devices:
        idx = _parse_ow_device_index(d)
        if idx is None:
            continue
        if d.type == "IN":
            if idx in in_indices_seen:
                return None, "Duplicate IN index: %s" % idx
            in_indices_seen.add(idx)
            ins.append(idx)
        elif d.type == "Q":
            if idx in q_indices_seen:
                return None, "Duplicate Q index: %s" % idx
            q_indices_seen.add(idx)

        node = _ow_simulation_node_index(d, n_q)
        if _ow_angle_specified(d):
            angle_deg = float(d.angle)
            angle_rad = angle_deg * math.pi / 180.0
            observables.append([node, angle_rad])
        if _ow_result_specified(d):
            results.append([node, int(d.result)])

    ins.sort()
    observables.sort(key=lambda x: x[0])
    results.sort(key=lambda x: x[0])
    return (graph, ins, observables, results), None


def _format_ow_vector_latex(mat):
    import sympy as sp
    rows = []
    for i in range(mat.rows):
        val = mat[i, 0]
        try:
            rows.append(sp.latex(val.evalf()))
        except Exception:
            rows.append(str(val))
    if not rows:
        return "\\[ \\mathbf{0} \\]"
    body = " \\\\ ".join(rows)
    return "\\[ \\begin{pmatrix} " + body + " \\end{pmatrix} \\]"


@with_ndb_context
def ConstructOWCircuit(project_key):
    try:
        proj = Project.get(project_key)
        if not proj:
            return json.dumps({"error": True, "data": "No project"})
        user_email = current_user_email()
        proj_user = normalize_user_value(proj.user)
        if proj_user and proj_user != user_email:
            return json.dumps({"error": True, "data": "Not authorized"})
        devices = OWDevice.query(ancestor=proj.key).fetch(1000)
        conns = OWConnection.query(ancestor=proj.key).fetch(1000)
        inputs, error = _build_ow_simulation_inputs(devices, conns)
        if error:
            return json.dumps({"error": True, "data": error})
        graph, ins, observables, results = inputs
        vec = owqc.universal_transformation(graph, ins, observables, results)
        return json.dumps({"error": False, "data": _format_ow_vector_latex(vec)}, default=str)
    except Exception as ex:
        return json.dumps({"error": True, "data": str(ex)}, default=str)


@with_ndb_context
def ConstructCircuit(project_key):
    try:
        proj = Project.get(project_key)
        if not proj:
            return "No project"
        user_email = current_user_email()
        proj_user = normalize_user_value(proj.user)
        if proj_user and proj_user != user_email:
            return "Not authorized"
        if not proj_user and user_email:
            proj.user = user_email
            proj.put()

        # check if we already did the calculation
        circuit = LOCircuit.query(ancestor=proj.key).fetch(1)
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
        circ = LOCircuit(parent=proj.key)
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

