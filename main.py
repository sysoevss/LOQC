# coding=UTF-8
'''
Created on 07.04.2022

@author: sysoev
'''
import webapp2
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import users

import os
import json
import data
import loqc

#
#  Login etc   
# 

class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            template_values = {
                'isAdmin': False
            }
            path = os.path.join(os.path.dirname(__file__), 'main.html')
            self.response.out.write(template.render(path, template_values))  
        else:
            self.redirect('/my')
            return 

class LoginPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            login_page = users.create_login_url('/')
            self.redirect(login_page)
            return 
        else:
            self.redirect('/my')
            return 

class LogoutPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            logout_page = users.create_logout_url('/')
            self.redirect(logout_page)
            return 
        else:
            self.redirect('/')
            return 

class ProjectsPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            login_page = users.create_login_url('/')
            self.redirect(login_page)
            return         
        else:
            template_values = {}
            path = os.path.join(os.path.dirname(__file__), 'projects.html')
            self.response.out.write(template.render(path, template_values))  


#
#  Common object methods   
# 

class CycleObjects(webapp2.RequestHandler):
    def get(self):
        object_type = self.request.get('object_type')
        parent_key = self.request.get('parent_key')
        self.response.out.write(data.CycleObjects(object_type, parent_key))
class GetObjectByKey(webapp2.RequestHandler):
    def get(self):
        object_type = self.request.get('object_type')
        key = self.request.get('key')
        self.response.out.write(data.GetObjectByKey(object_type, key))  
class DeleteCycleObject(webapp2.RequestHandler):
    def get(self):
        object_type = self.request.get('object_type')
        key = self.request.get('key')
        self.response.out.write(data.DeleteCycleObject(key, object_type))     
class AddCycleObject(webapp2.RequestHandler):
    def post(self):
        object_type = self.request.get('object_type')
        parent_key = self.request.get('parent_key')        
        dat = self.request.get('data')
        self.response.out.write(data.AddCycleObject(dat, object_type, parent_key))     
class EditCycleObject(webapp2.RequestHandler):
    def post(self):
        object_type = self.request.get('object_type')
        dat = self.request.get('data')
        key = self.request.get('key')
        self.response.out.write(data.EditCycleObject(key, dat, object_type)) 

class LODesigner(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.response.out.write("Re-login please")
        else:
            project_key = self.request.get('id')
            if project_key == "0":
                self.response.out.write("<html></html>")  
            else:
                projs = data.getProjects()
                projects = []
                for p in projs:
                    if str(p.key()) != project_key and p.name != "ParentOfAllProjects3717481125":
                        projects.append({'key': p.key(), 'name': p.name})
                template_values = {'project_key': project_key, 'projects': projects}
                path = os.path.join(os.path.dirname(__file__), 'lo_designer.html')
                self.response.out.write(template.render(path, template_values))  
class ClearDesign(webapp2.RequestHandler):
    def get(self):
        project_key = self.request.get('id')
        self.response.out.write(data.ClearProjectDesign(project_key))  
class Simulate(webapp2.RequestHandler):
    def get(self):
        project_key = self.request.get('project_key')
        self.response.out.write(data.ConstructCircuit(project_key))  
class SimulateCGate(webapp2.RequestHandler):
    def get(self):
        project_key = self.request.get('project_key')
        gate = self.request.get('gate')
        res, error = loqc.get_cgate_run(project_key, gate)
        if error:
            self.response.out.write(error)  
        else:            
            self.response.out.write(res)  
class PublishProject(webapp2.RequestHandler):
    def post(self):
        key = self.request.get('key')
        png = self.request.get('png')
        self.response.out.write(data.PublishProject(key, png)) 
class CopyProject(webapp2.RequestHandler):
    def get(self):
        key = self.request.get('key')
        self.response.out.write(data.CopyProject(key))   
class GetMatrices(webapp2.RequestHandler):
    def get(self):
        key = self.request.get('project_key')
        self.response.out.write(data.GetMatrices(key))  
class GetLibrary(webapp2.RequestHandler):
    def get(self):
        self.response.out.write(data.GetLibrary()) 
class GetFidelity(webapp2.RequestHandler):
    def get(self):
        key = self.request.get('project_key')
        errors = (self.request.get('errors') == "true")
        self.response.out.write(loqc.get_fidelity(key, errors))          

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
                                       ('/get_fidelity/', GetFidelity)], 
                                     debug=True)
