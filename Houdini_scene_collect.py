import os, shutil, json, time


class HSC(object): # HoudiniSceneCollect
    def __init__(self, job="C:/collect_folder"):
        self.job = job
        self.log_dir = os.path.join(self.job, "log")
        self.tex_dir = os.path.join(self.job, "tex")
        self.geo_dir = os.path.join(self.job, "geo")
        self.scenes_dir = os.path.join(self.job, "scenes")
        self.restore_json = None
        self.error_log = None
        self.excluded_node_type = ("ifd", "rop_geometry")
        self.geo_ext = (".abc",\
                        ".obj",\
                        ".bgeo",\
                        ".bgeo.sc",\
                        ".sc",\
                        ".fbx",
                        ".3ds")
        self.excluded_ext = (".ocio")
        self.sel_nodes = []
        self.restore_dict = {}
        self.error_list = []
        self.progress = 0
        self.changes_accept = 1
        self.copy_accept = 1

    def check(self):
        self.changes_accept = 0
        self.copy_accept = 0
        self.collect()

    def collect(self):
        self.makeFolder(self.job)
        self.makeFolder(self.log_dir)
        self.__selectNodes()
        self.__processing()
        if self.changes_accept:
            self.__saveHipfile()
            hou.putenv("JOB", self.job)

    def makeFolder(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def __selectNodes(self):
        if hou.selectedNodes():
            for node in hou.selectedNodes():
                self.sel_nodes.append(node)
                for s in node.allSubChildren(top_down=True, recurse_in_locked_nodes=False):
                    self.sel_nodes.append(s)
        else:
            self.sel_nodes = hou.node("/").allSubChildren(top_down=True, recurse_in_locked_nodes=False)

    def __processing(self):        
        for n in self.sel_nodes:
            self.__progressShow()
            for parm in n.parms():
                self.__checkParm(parm)
        print "Collect complete!"

    def __progressShow(self):
        count = 100.0/len(self.sel_nodes)
        self.progress += count
        print "Progress: %d" % int(self.progress) + "%"        

    def __checkParm(self, parm):
        # Check the parm type and run copy for that data type.
        if not parm.isDisabled():
            if parm.parmTemplate().type() == hou.parmTemplateType.String:
                if parm.node().type().name() not in self.excluded_node_type:
                    parm_eval_dir = os.path.dirname(parm.eval())
                    if os.path.exists(parm_eval_dir):
                        if "$F" in parm.unexpandedString():
                            self.__copySeq(parm)
                        elif r"%(UDIM)d" in parm.unexpandedString() or "<UDIM>" in parm.unexpandedString():
                            self.__copyUDIM(parm)
                        else:
                            self.__copyFile(parm)

    def __copyFile(self, parm): # Need more tests
            # Check type geo or tex.
            name, ext = os.path.splitext(os.path.basename(parm.unexpandedString()))
            if ext.lower() in self.geo_ext:
                file_type = "geo"
            else:
                file_type = "tex"
            # Data for copy.
            old_path = parm.eval()
            fullName = os.path.basename(old_path)
            new_dir = os.path.join(self.job, file_type).replace("\\", "/")
            new_path = os.path.join(new_dir, fullName).replace("\\", "/")
            old_string = parm.unexpandedString()
            new_string = "$JOB/%s/%s" % (file_type, fullName)
            data = dict(node=parm.node().path(),
                        parm = parm.path(),
                        parm_name=parm.name(),
                        ext=ext.lower(),
                        #path_old=old_path,
                        #path_new=new_path,
                        string_old=old_string,                    
                        string_new=new_string)
            self.makeFolder(new_dir)
            # copy
            rename_parm_status = 0
            if self.__checkExistance(old_path):
                if not self.__checkExistance(new_path):
                    if self.copy_accept:
                        shutil.copy2(old_path, new_path)
                        rename_parm_status = 1
                self.__saveLog(data)                
            else:
                self.__saveLog(parm.path(), 1)
            if rename_parm_status:
                if self.changes_accept:
                    parm.set(new_string)
    
    def __copyUDIM(self, parm): # Need more tests
        def b(x):
            if type(x) == str:
                while x.endswith("_") or x.endswith(".") or x.endswith("-"):
                    x = x[:-1]
                return x
            else:
                print "begin have to be the string type."
        old_dir = os.path.dirname(parm.unexpandedString())
        old_name = os.path.basename(parm.unexpandedString())
        old_string = parm.unexpandedString()
        if r"%(UDIM)d" in old_string:
            begin, end = old_name.split(r"%(UDIM)d")
        if "<UDIM>" in old_string:
            begin, end = old_name.split("<UDIM>")

        
        ext = os.path.splitext(parm.unexpandedString())[-1]
        files = [x for x in os.listdir(old_dir) if x.startswith(begin) and x.endswith(end)]
        begin = b(begin)
        new_dir = os.path.join(self.job, "tex", "UDIM_" + begin)
        self.makeFolder(new_dir)
        rename_parm_status = 0
        for f in files:
            old_path = os.path.join(old_dir, f).replace("\\", "/")
            new_path = os.path.join(new_dir, f).replace("\\", "/")
            if self.__checkExistance(old_path):
                if not self.__checkExistance(new_path):
                    if self.copy_accept:
                        shutil.copy2(old_path, new_path)
                        rename_parm_status = 1
            else:
                self.__saveLog(parm.path(), 1)

        new_name = begin + "%(UDIM)d" + end
        new_string = "$JOB/tex/" + begin + "UDIM/" + new_name
        data = dict(node=parm.node().path(),
                    parm = parm.path(),
                    parm_name=parm.name(),
                    ext=ext.lower(),
                    #path_old=old_path,
                    #path_new=new_path,
                    string_old=old_string,                    
                    string_new=new_string)
        
        self.__saveLog(data)

        if rename_parm_status:
            if self.changes_accept:
                parm.set(new_string)

    def __copySeq(self, parm):
        old_string = parm.unexpandedString()
        old_dir = os.path.dirname(parm.eval())
        name = os.path.basename(old_string)
        new_folder = name.split("$F")[0]
        ext = name.split("$F")[-1]

        # define name for new folder
        sign = ("-", "_", " ", ".")
        while new_folder[-1] in sign:
            new_folder = new_folder[:-1]
        prefix = new_folder

        # identify class
        ext = os.path.splitext(old_string)[1]
        if ext in self.geo_ext:
            cl = "geo"
        else:
            cl = "tex"

        # identify padding
        padding = ""
        if (name.split("$F")[1][0]).isdigit():
            padding = int(name.split("$F")[1][0])


        # make new directory for the sequence
        new_dir = os.path.join(self.job, cl, prefix)
        self.makeFolder(new_dir)

        # identify sequence for peocessing
        seq_list = [f for f in os.listdir(old_dir) if f.startswith(prefix)]

        # copy sequence
        rename_parm_status = 0
        for f in seq_list:
            old_path = os.path.join(old_dir, f).replace("\\", "/")
            new_path = os.path.join(new_dir, f).replace("\\", "/")
            if self.__checkExistance(old_path):
                if self.copy_accept:
                    shutil.copy2(old_path, new_path)
                    rename_parm_status = 1
            else:
                self.__saveLog(parm.path(), 1)
        # set new parm
        new_string = ("$JOB/%s/%s/%s" % (cl, prefix, os.path.basename(old_string))).replace("\\", "/")
        data = dict(node=parm.node().path(),
                    parm = parm.path(),
                    parm_name=parm.name(),
                    ext=ext.lower(),
                    #path_old=old_path,
                    #path_new=new_path,
                    string_old=old_string,                    
                    string_new=new_string)

        self.__saveLog(data)

        if rename_parm_status:
            if self.changes_accept:
                parm.set(new_string)

    def __saveHipfile(self):
        self.makeFolder(self.scenes_dir)
        hip_file = os.path.join(self.scenes_dir, hou.hipFile.name())
        hou.hipFile.save(hip_file)

    def __saveLog(self, data=None, err=None):       
        self.restore_json = os.path.join(self.log_dir, "restore.json")
        self.error_json = os.path.join(self.log_dir, "errors.json")
        if data:
            if not err:
                self.restore_dict[data["parm"]] = data["string_old"]
                with open(self.restore_json, 'w') as f:
                    json.dump(self.restore_dict, f, indent=4)
            else:
                self.error_list.append(data)
                with open(self.error_json, 'w') as f:
                    json.dump(self.error_list, f, indent=4)
                
    def restore(self):
        self.restore_json = os.path.join(self.log_dir, "restore.json")
        with open(self.restore_json) as f:
            data = json.load(f)
        if data:
            for k, v in data.items():
                hou.parm(k).set(v)
        print "Restore complete!"

    def __checkExistance(self, path):
        if os.path.exists(path):
            return True
        else:
            return False


c = HSC("D:/collect_test")
c.check()