# This Python file uses the following encoding: utf-8

#Classes for wrf4g


import rlcompleter
import readline
import time
import datetime
import string
from commands import getstatusoutput
import re
import os.path
from wrf4g.wrf4gapp.models import *




# Class Experiment

class Experiment:
    """ Class experiment
          atributes:
                    name (string)
                    start_date (date)
                    end_date (date)
                    status (Options=[D,R,S,Q],done,run,schedule,queue)
                    experiment_db (Object Experiment_db from wrf4g.wrf4gapp.models,
                                   to use de data base wrf4g.)
           
          functions:
                    
                    get_Name()
                    get_Id(name)
                    get_Start_Date()
                    set_Start_Date(start_date)
                    get_End_Date()
                    set_End_Date(end_date)
                    get_Status()
                    set_Status(status)
    """
                    
                   
      


    def __init__(self,name,verbose=0):
        self.name=name
        self.experiment_db=Experiment_db()
        self.verbose=verbose
        self.end_date=""
        self.start_date=""
        self.status=""
       
        #check if the experiment exists
        try:
            Experiment_db.objects.get(name=self.name)
        except: # if it does not exists 
            #Create the experiment in the data base if it does not exist
            self.experiment_db.name=self.name
            self.experiment_db.save()
        else:
            #If it have already existed, load it in self.experiment_db
            self.experiment_db=Experiment_db.objects.get(name=self.name)
        

    def get_Id(self):
        self.experiment_db=Experiment_db.objects.get(name=self.name)
        self.id=self.experiment_db.id
        if self.verbose==1:
            print "Getting id %s of the experiment  %s"%(self.name,self.id)
        return self.id

    def get_Start_Date(self):
        self.experiment_db=Experiment_db.objects.get(name=self.name)
        self.start_date=self.experiment_db.start_date
        if self.verbose==1:
            print "Getting Start Date %s of the experiment %s"%(self.start_date,self.name)
        return self.start_date
        
    def set_Start_Date(self,start_date):
        self.start_date=start_date 
        self.experiment_db.start_date=self.start_date
        self.experiment_db.save()
        if self.verbose==1:
           print "Setting Start Date  %s of the  experiment %s"%(self.start_date,self.name)

    def get_End_Date(self):
        self.experiment_db=Experiment_db.objects.get(name=self.name)
        self.end_date=self.experiment_db.end_date
        if self.verbose==1:
           print "Getting End Date  %s of the  experiment %s"%(self.end_date,self.name)
        return self.end_date
        
    def set_End_Date(self,end_date):
	self.end_date=end_date
        self.experiment_db.end_date=self.end_date
        self.experiment_db.save()
        if self.verbose==1:
           print "Setting End Date of the  experiment %s"%(self.end_date,self.name)
       
                       
    def get_Status(self):
	""" Status of the  experiment : D,R,S,Q Done,Run,Schedule,Queue"""
        self.experiment_db=Experiment_db.objects.get(name=self.name)
        self.status=self.experiment_db.status		
        if self.verbose==1:
           print "Getting the estatus %s of the  experiment %s %s-%s"%(self.status,self.name,self.start_date,self.end_date)
        return self.status
          
    def set_Status(self,status):
	""" Status of the  experiment : D,R,S,Q Done,Run,Schedule,Queue"""
	self.status=status
        self.experiment_db.status=self.status
        self.experiment_db.save()	
	if self.verbose==1:
           print "Getting the estatus %s of the  experiment %s %s-%s"%(self.status,self.name,self.start_date,self.end_date)
              
    

		
# Class Realization

class Realization:
    """ Class Realization
          atributes:
                    name (string)
                    start_date (datetime)
                    end_date (datetime)
                    exp (id of the experiment)
                    realization_db (Object Realization_db from wrf4g.wrf4gapp.models,
                                   to use de data base wrf4g.)
           
          functions:
                    get_Id(self):
                    get_Start_Date(self)
                    set_Start_Date(self,start_date)
                    get_End_Date(self)
                    set_End_Date(self,end_date)
                    get_Exp(self)
                    set_Exp(self,status)
    """
                    
                   
      


    def __init__(self,name,*verbose,):
        self.name=name
        self.realization_db=Realization_db()
        self.verbose=verbose
        self.end_date=""
        self.start_date=""
        self.exp=0
        #check if the realization exists
        try:
            Realization_db.objects.get(name=self.name)
        except : # if it does not exist
            #Create the realization in the data base if it does not exist
            self.realization_db.name=self.name
            self.realization_db.save()
        else:
            #If it have already existed, load it in self.experiment_db
            self.realization_db=Realization_db.objects.get(name=self.name)
  
    def get_Id(self):
        self.realization_db=Realization_db.objects.get(name=self.name)
        self.id=self.realization_db.id
        if self.verbose==1:
            print "Getting id %s of the experiment  %s"%(self.name,self.id)
        return self.id


    def get_Start_Date(self):
        self.realization_db=Realization_db.objects.get(name=self.name)
        self.start_date=self.realization_db.start_date
        if self.verbose==1:
            print "Getting Start Date %s of the realization %s"%(self.start_date,self.name)
        return self.start_date

    def set_Start_Date(self,start_date):
        self.start_date=start_date 
        self.realization_db.start_date=self.start_date
        self.realization_db.save()
        if self.verbose==1:
           print "Setting Start Date  %s of the  realization_db %s"%(self.start_date,self.name)      
 
    def get_End_Date(self):
        self.realization_db=Realization_db.objects.get(name=self.name)
        self.end_date=self.realization_db.end_date
        if self.verbose==1:
           print "Getting End Date  %s of the realization %s"%(self.end_date,self.name)
        return self.end_date
        
    def set_End_Date(self,end_date):
        self.end_date=end_date 
        self.realization_db.end_date=self.end_date
        self.realization_db.save()
        if self.verbose==1:
           print "Setting End Date of the realization %s"%(self.end_date,self.name)
       
    def get_Exp(self):
        self.realization_db=Realization_db.objects.get(name=self.name)
        self.exp=self.realization_db.exp.id
        if self.verbose==1:
           print "Getting experiment id  %s of the realization %s"%(self.exp,self.name)
        return self.exp
                    
    def set_Exp(self,exp):   
        self.exp=exp
        self.realization_db.exp_id=self.exp
        self.realization_db.save()  
        if self.verbose==1:
           print "Setting experiment  %s of the realization %s"%(self.exp,self.name)
        
    

    

# Class Chunk

class Chunk:
    """ Class chunk
          atributes:
                    name (string)
                    rea (id of the realization)
                    start_date (datetime)
                    end_date (datetime)
                    current_date(datetime)
                    wps_file 0/1 (True/False) indicates !!! 
                    status (Options=[D,R,S,Q],done,run,schedule,queue)
                    chunk_db (Object Chunk_db from wrf4g.wrf4gapp.models,
                                   to use de data base wrf4g.)
           
          functions:
                    get_Id(self)
                    get_Start_Date(self)
                    set_Start_Date(self,start_date)
                    get_End_Date(self)
                    set_End_Date(self,end_date)
                    get_Current_Date(self)
                    set_Current_Date(self,current_date)
                    get_Wps_File(self)
                    set_Wps_File(self,wps_file)
                    get_Status(self)
                    set_Status(self,status)
    """
                    
                   
      


    def __init__(self,name,*verbose):
        self.name=name
        self.chunk_db=Chunk_db()
        self.verbose=verbose
        self.end_date=""
        self.start_date=""
        self.current_date=""
        self.wps_file=0 ### be careful!!
        self.status=""
        self.rea=0
        #check if the chunk exists
        try:
            Chunk_db.objects.get(name=self.name)
        except : # if it does not exist
            #Create the chunk in the data base if it does not exist
            self.chunk_db.name=self.name
            self.chunk_db.save()
        else:
            #If it have already existed, load it in self.experiment_db
            self.chunk_db=Chunk_db.objects.get(name=self.name)
  


    def get_Id(self):
        self.chunk_db=Chunk_db.objects.get(name=self.name)
        self.id=self.chunk_db.id
        if self.verbose==1:
            print "Getting id %s of the experiment  %s"%(self.name,self.id)
        return self.id


    def get_Start_Date(self):
        self.chunk_db=Chunk_db.objects.get(name=self.name)
        self.start_date=self.chunk_db.start_date
        if self.verbose==1:
            print "Getting Start Date %s of the chunk %s"%(self.start_date,self.name)
        return self.start_date
        
    def set_Start_Date(self,start_date):
        self.start_date=start_date 
        self.chunk_db.start_date=self.start_date
        self.chunk_db.save()
        if self.verbose==1:
           print "Setting Start Date  %s of the  chunk %s"%(self.start_date,self.name)


    def get_End_Date(self):
        self.chunk_db=Chunk_db.objects.get(name=self.name)
        self.end_date=self.chunk_db.end_date
        if self.verbose==1:
           print "Getting End Date  %s of the  chunk %s"%(self.end_date,self.name)
        return self.end_date
        
    def set_End_Date(self,end_date):
	self.end_date=end_date
        self.chunk_db.end_date=self.end_date
        self.chunk_db.save()
        if self.verbose==1:
           print "Setting End Date of the  chunk %s"%(self.end_date,self.name)       
                       
 
    def get_Current_Date(self):
        self.chunk_db=Chunk_db.objects.get(name=self.name)
        self.current_date=self.chunk_db.current_date
        if self.verbose==1:
           print "Getting the current_date %s of the  chunk %s %s-%s"%(self.current_date,self.name,self.start_date,self.end_date)
        return self.current_date
        
    def set_Current_Date(self,current_date):
        self.current_date=current_date
        self.chunk_db.current_date=self.current_date
        self.chunk_db.save()
        if self.verbose==1:
           print "Setting the current_date %s of the  chunk %s %s-%s"%(self.current_date,self.name,self.start_date,self.end_date)
        
        
    def get_Wps_File(self):
        """ wps_file has values True or False and indicates !!! """
        self.chunk_db=Chunk_db.objects.get(name=self.name)
        self.wps_file=self.chunk_db.wps_file
        if self.verbose==1:
           print "Getting the wps_file %s of the  chunk %s %s-%s"%(self.wps_file,self.name,self.start_date,self.end_date)
        return self.wps_file

    def set_Wps_File(self,wps_file):
        """ wps_file has values True or False and indicates !!! """
        self.wps_file=wps_file
        self.chunk_db.wps_file=self.wps_file
        self.chunk_db.save()
        if self.verbose==1:
           print "Setting the wps_file %s of the  chunk %s %s-%s"%(self.wps_file,self.name,self.start_date,self.end_date)


    def get_status(self):
        """ Status of the  chunk : D,R,S,Q Done,Run,Schedule,Queue"""	
        self.chunk_db=Chunk_db.objects.get(name=self.name)
        self.status=self.chunk_db.status	
        if self.verbose==1:
           print "Getting the estatus %s of the  chunk %s %s-%s"%(self.status,self.name,self.start_date,self.end_date)
        return self.status
          
    def set_status(self,status):
        """ Status of the  chunk : D,R,S,Q Done,Run,Schedule,Queue"""	
        self.status=status
        self.chunk_db.status=self.status
        self.chunk_db.save()
        if self.verbose==1:
           print "Getting the estatus %s of the chunk %s %s-%s"%(self.status,self.name,self.start_date,self.end_date)

    def get_Rea(self):
        self.chunk_db=Chunk_db.objects.get(name=self.name)
        self.rea=self.chunk_db.rea.id
        if self.verbose==1:
           print "Getting experiment id  %s of the realization %s"%(self.exp,self.name)
        return self.rea
                    
    def set_Rea(self,rea):   
        self.rea=rea
        self.chunk_db.rea_id=self.rea
        self.chunk_db.save()  
        if self.verbose==1:
           print "Setting experiment  %s of the realization %s"%(self.rea,self.name)
 




# Class File_Type

class File_Type:
    """ Class File_Type
          atributes:
                    type_ (type of the file)
                    freq_h(3h or 6h)         
                    file_type_db (Object File_db from wrf4g.wrf4gapp.models,
                                   to use de data base wrf4g.)
           
          functions:
                    get_Type(self)
                    set_Type(self,type_)
                    get_Freq_H(self)
                    set_Freq_H(self,freq_h)
    """
                    
                   
      


    def __init__(self,name,*verbose):
        self.name=name
        self.file_type_db=File_Type_db()               
        self.verbose=verbose
        
        #check if the file_type exists
        try:
            File_type_db.objects.get(name=self.name)
        except : # if it does not exist
            #Create the file_type in the data base if it does not exist
            self.file_type_db.name=self.name
            self.file_type_db.save()
        else:
            #If it have already existed, load it in self.experiment_db
            self.file_type_db=File_Type_db.objects.get(name=self.name)
  

    def get_Type(self):
        
        if self.verbose==1:
            print "Getting type %s of the file_type id %s "%(self.type_,self.id)
        return self.type_
        
    def set_Type(self,type_):
        self.type_=type_ 
        if self.verbose==1:
           print "Setting type  %s of the  file_type id %s"%(self.type_,self.id)

    def get_Freq_H(self):
        if self.verbose==1:
           print "Getting freq_h %s of the  file_type id %s"%(self.freq_h,self.id)
        return self.freq_h

        
    def set_Freq_H(self,freq_h):
        self.freq_h=freq_h
        if self.verbose==1:
           print "Setting freq_h %s of the  file_type id %s"%(self.freq_h,self.id)
        





# Class File

class File:
    """ Class File
          atributes:
                    type (id of the filetype)
                    path(path of the file)
                    rea(id of the realization)
                    start_date (datetime)
                    end_date (datetime)                
                    file_db (Object File_db from wrf4g.wrf4gapp.models,
                                   to use de data base wrf4g.)
           
          functions:
                    get_Id()
                    get_Type()
                    set_Type(type)
                    get_Path()
                    set_Path(path)
                    get_Rea()
                    set_Rea(rea)
                    get_Start_Date()
                    set_Start_Date(start_date)
                    get_End_Date()
                    set_End_Date(end_date)
                 
    """
                    
                   
      


    def __init__(self,name,*verbose):
        self.name=name
        self.file_db=File_db()
        self.start_date=""
        self.end_date=""
        self.rea=0
        self.type_=0
        self.path=""       
        self.verbose=verbose
        self.type_file_id=0
      
        #check if the file exists
        try:
            File_db.objects.get(name=self.name)
        except : # if it does not exist
            #Create the file in the data base if it does not exist
            self.file_db.name=self.name
            self.file_db.save()
        else:
            #If it have already existed, load it in self.file_db
            self.file_db=File_db.objects.get(name=self.name)
  


    def get_Id(self):
        self.file_db=File_db.objects.get(name=self.name)
        self.id=self.file_db.id
        if self.verbose==1:
            print "Getting id %s of the experiment  %s"%(self.name,self.id)
        return self.id


    def get_Start_Date(self):
        self.file_db=File_db.objects.get(name=self.name)
        self.start_date=self.file_db.start_date
        if self.verbose==1:
            print "Getting Start Date %s of the chunk %s"%(self.start_date,self.name)
        return self.start_date
        
    def set_Start_Date(self,start_date):
        self.start_date=start_date 
        self.file_db.start_date=self.start_date
        self.file_db.save()
        if self.verbose==1:
           print "Setting Start Date  %s of the  chunk %s"%(self.start_date,self.name)


    def get_End_Date(self):
        self.file_db=File_db.objects.get(name=self.name)
        self.end_date=self.file_db.end_date
        if self.verbose==1:
           print "Getting End Date  %s of the  chunk %s"%(self.end_date,self.name)
        return self.end_date
        
    def set_End_Date(self,end_date):
	self.end_date=end_date
        self.file_db.end_date=self.end_date
        self.file_db.save()
        if self.verbose==1:
           print "Setting End Date of the  chunk %s"%(self.end_date,self.name)       

 
    #en estas dos funciones me dice que la tabla file_db no tiene atributo type!! hay que hacer type.id     

    def get_Type(self):
        self.file_db=File_db.objects.get(name=self.name)
        self.type_=self.file_db.type  
        if self.verbose==1:
           print "Getting type id  %s of the  file id %s"%(self.type_,self.id)
        return self.type_
                    
    def set_Type(self,type_):          	
        self.type_=type_
        self.file_db.type=self.type
        self.file_db.save()           
        if self.verbose==1:
           print "Setting  type id  %s of the file %s"%(self.type_,self.id)




    def get_Rea(self):
        self.file_db=File_db.objects.get(name=self.name)
        self.rea=self.file_db.rea.id
        if self.verbose==1:
           print "Getting  realization id  %s of the file id %s"%(self.rea,self.id)
        return self.rea
                    
    def set_Rea(self,rea): 
        self.rea=rea
        self.file_db.rea_id=self.rea
        self.file_db.save()   
        if self.verbose==1:
           print "Setting   realization id  %s of the file id %s"%(self.rea,self.id)
   
    def get_Path(self):
        self.file_db=File_db.objects.get(name=self.name)
        self.path=self.file_db.path
        if self.verbose==1:
           print "Getting  path  %s of the file id %s"%(self.path,self.id)
        return self.path
                    
    def set_Path(self,exp):     
        self.exp=exp         
        self.file_db.path=self.path
        self.file_db.save()   
        if self.verbose==1:
           print "Setting   path  %s of the file id %s"%(self.path,self.id) 





