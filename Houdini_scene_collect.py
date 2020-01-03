import os, shutil


class HSC(object): # HoudiniSceneCollect
    def __init__(self, job="C:/collect_folder"):
        self.job = job
        self.tex_dir = os.path.join(self.job, "tex")
        self.geo_dir = os.path.join(self.job, "geo")
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
        self.changes_accept = 1
        self.copy_accept = 1

    def emulation(self):
        self.changes_accept = 0
        self.copy_accept = 0
        self.collect()

    def collect(self):
        self.makeFolder(self.job)
        self.__selectNodes()
        self.__processing()
        if self.changes_accept:
            hou.putenv("job", self.job)

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
            for parm in n.parms():
                self.__checkParm(parm)

    def __checkParm(self, parm):
        # Check the parm type and run copy for that data type.
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
        data = dict(node=parm.node(),
                    parameter=parm.name(),
                    type="%s file" % ext.lower(),
                    old_path=old_path,
                    old_string=old_string,
                    new_path=new_path,
                    new_string=new_string)
        self.makeFolder(new_dir)
        # copy
        rename_parm_status = 0
        if self.__checkExistance(old_path):
            if not self.__checkExistance(new_path):
                if self.copy_accept:
                    shutil.copy(old_path, new_path)
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
        begin, end = old_name.split("%(UDIM)d")
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
                        shutil.copy(old_path, new_path)
                        rename_parm_status = 1
        new_name = begin + "%(UDIM)d" + end
        new_parm = "$JOB/tex/" + begin + "UDIM/" + new_name
        if rename_parm_status:
            if self.changes_accept:
                parm.set(new_parm)

    def __copySeq(self, parm): # In development.
        parm_str = parm.unexpandedString()
        old_dir = os.path.dirname(parm.eval())
        name = os.path.basename(parm_str)
        name = os.path.basename(parm_str)
        prefix = name.split("$F")[0]
        padding = ""
        if (name.split("$F")[1][0]).isdigit():
            padding = name.split("$F")[1][0]
        # check type
        # copy
        # set new parameter value
        # log changes
        pass

    def __saveHipfile(self):
        pass

    def __saveLog(self, data=None):
        if data:
            print data["node"]
        else:
            print "No data to show."

    def __checkExistance(self, path):
        if os.path.exists(path):
            return True
        else:
            return False


w = HSC("D:/collect_test")
w.emulation()