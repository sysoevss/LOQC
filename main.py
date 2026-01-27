# coding=UTF-8
'''
Created on 07.04.2022

@author: sysoev
'''
import os
import json
import urllib.parse

import webapp2
import jinja2

import users_compat as users

import data
import loqc

#
#  Login etc   
# 

_TEMPLATE_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    autoescape=True,
)


def _render_template(filename, values):
    template = _TEMPLATE_ENV.get_template(filename)
    return template.render(values or {})


class BaseHandler(webapp2.RequestHandler):
    def dispatch(self):
        users.set_request_environ(self.request.environ)
        try:
            with data.ndb_context():
                super(BaseHandler, self).dispatch()
        finally:
            users.clear_request_environ()


class MainPage(BaseHandler):
    def get(self):
        #user = users.get_current_user()
        #if not user:
        template_values = {
            'isAdmin': False
        }
        self.response.write(_render_template('main.html', template_values))
        #else:
        #    self.redirect('/my')
        #    return 

class LoginPage(BaseHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect('/my')
            return
        continue_to = self.request.get('continue') or '/my'
        self.redirect(continue_to)
        return

class LogoutPage(BaseHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            logout_page = 'https://accounts.google.com/Logout'
            self.redirect(logout_page)
            return
        else:
            self.redirect('/')
            return 

class ProjectsPage(BaseHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            login_page = users.create_login_url('/')
            self.redirect(login_page)
            return         
        else:
            template_values = {}
            self.response.write(_render_template('projects.html', template_values))


#
#  Common object methods   
# 

class CycleObjects(BaseHandler):
    def get(self):
        object_type = self.request.get('object_type')
        parent_key = self.request.get('parent_key')
        self.response.out.write(data.CycleObjects(object_type, parent_key))
class GetObjectByKey(BaseHandler):
    def get(self):
        object_type = self.request.get('object_type')
        key = self.request.get('key')
        self.response.out.write(data.GetObjectByKey(object_type, key))  
class DeleteCycleObject(BaseHandler):
    def get(self):
        object_type = self.request.get('object_type')
        key = self.request.get('key')
        self.response.out.write(data.DeleteCycleObject(key, object_type))     
class AddCycleObject(BaseHandler):
    def post(self):
        object_type = self.request.get('object_type')
        parent_key = self.request.get('parent_key')        
        dat = self.request.get('data')
        self.response.out.write(data.AddCycleObject(dat, object_type, parent_key))     
class EditCycleObject(BaseHandler):
    def post(self):
        object_type = self.request.get('object_type')
        dat = self.request.get('data')
        key = self.request.get('key')
        self.response.out.write(data.EditCycleObject(key, dat, object_type)) 

class LODesigner(BaseHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.response.write("Re-login please")
        else:
            project_key = self.request.get('id')
            if project_key == "0":
                self.response.write("<html></html>")
            else:
                projs = data.getProjects()
                projects = []
                for p in projs:
                    if data.key_to_str(p.key) != project_key and p.name != "ParentOfAllProjects3717481125":
                        projects.append({'key': data.key_to_str(p.key), 'name': p.name})
                template_values = {'project_key': project_key, 'projects': projects}
                self.response.write(_render_template('lo_designer.html', template_values))
class ClearDesign(BaseHandler):
    def get(self):
        project_key = self.request.get('id')
        self.response.write(data.ClearProjectDesign(project_key))
class Simulate(BaseHandler):
    def get(self):
        project_key = self.request.get('project_key')
        self.response.write(data.ConstructCircuit(project_key))
class SimulateCGate(BaseHandler):
    def get(self):
        project_key = self.request.get('project_key')
        gate = self.request.get('gate')
        res, error = loqc.get_cgate_run(project_key, gate)
        if error:
            self.response.write(error)
        else:            
            self.response.write(res)
class PublishProject(BaseHandler):
    def post(self):
        key = self.request.get('key')
        png = self.request.get('png')
        self.response.write(data.PublishProject(key, png))
class CopyProject(BaseHandler):
    def get(self):
        key = self.request.get('key')
        self.response.write(data.CopyProject(key))
class GetMatrices(BaseHandler):
    def get(self):
        key = self.request.get('project_key')
        self.response.write(data.GetMatrices(key))
class GetLibrary(BaseHandler):
    def get(self):
        self.response.write(data.GetLibrary())
class GetFidelity(BaseHandler):
    def get(self):
        key = self.request.get('project_key')
        errors = (self.request.get('errors') == "true")
        self.response.write(loqc.get_fidelity(key, errors))


class MigrateProjectUsers(BaseHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.response.write("Not authorized")
            return
        use_fallback = (self.request.get('use_fallback') == "true")
        fallback_email = data.current_user_email() if use_fallback else None
        self.response.write(data.MigrateProjectUsers(fallback_email=fallback_email))

application = webapp2.WSGIApplication([('/', MainPage),
                                       ('/login', LoginPage),
                                       ('/logout', LogoutPage),
                                       ('/my', ProjectsPage),
                                       ('/cycle_objects/', CycleObjects),
                                       ('/get_object_by_key/', GetObjectByKey),
                                       ('/add_cycle_object/', AddCycleObject),
                                       ('/delete_cycle_object/', DeleteCycleObject),
                                       ('/update_cycle_object/', EditCycleObject), 
                                       ('/lo_designer/', LODesigner),
                                       ('/clear_design/', ClearDesign),
                                       ('/simulate/', Simulate),
                                       ('/simulate_cgate/', SimulateCGate),
                                       ('/publish_project/', PublishProject),
                                       ('/copy_project/', CopyProject),
                                       ('/matrices/', GetMatrices),
                                       ('/get_library/', GetLibrary),
                                       ('/get_fidelity/', GetFidelity),
                                       ('/migrate_project_users/', MigrateProjectUsers)], 
                                     debug=True)
