import os, shutil, json


class HSC(object): # HoudiniSceneCollect
    def __init__(self, job="C:/collect_folder"):
        self.job = job
        self.log_dir = os.path.join(self.job, "log")
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
                        shutil.copy2(old_path, new_path)
                        rename_parm_status = 1
        new_name = begin + "%(UDIM)d" + end
        new_parm = "$JOB/tex/" + begin + "UDIM/" + new_name
        if rename_parm_status:
            if self.changes_accept:
                parm.set(new_parm)

    def __copySeq(self, parm):
        parm_str = parm.unexpandedString()
        old_dir = os.path.dirname(parm.eval())
        name = os.path.basename(parm_str)
        new_folder = name.split("$F")[0]

        # define name for new folder
        sign = ("-", "_", " ", ".")
        while new_folder[-1] in sign:
            new_folder = new_folder[:-1]

        # identify class
        ext = os.path.splitext(parm_str)[1]
        if ext in selg.geo_ext:
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
                data = "File $s is not exist." % old_path
                self.__saveLog(data)

        # set new parm
        new_parm_str = ("$JOB/%s/%s/%s" % (cl, prefix, os.path.basename(parm_str))).replace("\\", "/")
        if rename_parm_status:
            if self.changes_accept:
                parm.set(new_parm_str)

    def __saveHipfile(self):
        pass

    def __saveLog(self, data=None, err=None): # Developnemt started.
        success_log = os.path.join(self.log_dir, "success.txt")
        error_log = os.path.join(self.log_dir, "error.txt")
        restore_json = os.path.join(self.log_dir, "restore.json")
        if data:
            print data
        else:
            print "No data to show."

    def __checkExistance(self, path):
        if os.path.exists(path):
            return True
        else:
            return False


w = HSC("D:/collect_test")
w.emulation()