import os, shutil, json, time


class HSC(object): # HoudiniSceneCollect
    def __init__(self, job="C:/collect_folder"):
        self.job = job
        self.log_dir = os.path.join(self.job, "log")
        self.tex_dir = os.path.join(self.job, "tex")
        self.geo_dir = os.path.join(self.job, "geo")
        self.restore_json = None
        self.error_log = None
        self.excluded_node_type = ("ifd")
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
        self.progress = 0
        self.changes_accept = 1
        self.copy_accept = 1

    def emulate(self):
        self.changes_accept = 0
        self.copy_accept = 0
        self.collect()

    def collect(self):
        self.makeFolder(self.job)
        self.makeFolder(self.log_dir)
        self.__selectNodes()
        self.__processing()
        if self.changes_accept:
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
            time.sleep(0.01)
            for parm in n.parms():
                self.__checkParm(parm)

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
                        elif "%(UDIM)d" in parm.unexpandedString():
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
                    path_old=old_path,
                    path_new=new_path,
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
            print "This file doesn't exist: %s" % parm.path()
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
        old_dir = os.path.dirname(parm.eval())
        old_name = os.path.basename(parm.unexpandedString())
        old_string = parm.unexpandedString()
        begin, end = old_name.split("%(UDIM)d")
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
                if not self.__checkExistancepath_new():
                    if self.copy_accept:
                        shutil.copy2(old_path, new_path)
                        rename_parm_status = 1
        new_name = begin + "%(UDIM)d" + end
        new_string = "$JOB/tex/" + begin + "UDIM/" + new_name

        data = dict(node=parm.node().path(),
                    parm = parm.path(),
                    parm_name=parm.name(),
                    ext=ext.lower(),
                    path_old=old_path,
                    path_new=new_path,
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
        new_dir = os.path.join(self.job, cl, new_folder)
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
                print "File $s is not exist." % old_path

        # set new parm
        new_string = ("$JOB/%s/%s/%s" % (cl, prefix, os.path.basename(old_string))).replace("\\", "/")

        data = dict(node=parm.node().path(),
                    parm = parm.path(),
                    parm_name=parm.name(),
                    ext=ext.lower(),
                    path_old=old_path,
                    path_new=new_path,
                    string_old=old_string,                    
                    string_new=new_string)

        self.__saveLog(data)

        if rename_parm_status:
            if self.changes_accept:
                parm.set(new_string)

    def __saveHipfile(self):
        pass

    def __saveLog(self, data=None, err=None):       
        self.restore_json = os.path.join(self.log_dir, "restore.json")
        self.error_log = os.path.join(self.log_dir, "error.txt")
        if data:
            if not err:
                self.restore_dict[data["parm"]] = data["string_old"]
                with open(self.restore_json, 'w') as f:
                    json.dump(self.restore_dict, f, indent=4)
            else:
                print "No data to print."
                
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


w = HSC("D:/collect_test")
w.restore()