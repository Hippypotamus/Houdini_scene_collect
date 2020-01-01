import os, shutil

collect_folder = "D:/collect_test"


class HSC(object): # HoudiniSceneCollect
    def __init__(self, job="C:/", ):
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
        self.sel_nodes = None
        self.changes_accept = 0
        # start
        self.start()

    def start(self):
        self.makeFolder(self.job)
        self.__selectNodes()
        self.__processing()

    def makeFolder(self, path):
        if not os.path.exists(path):
            os.mkdir(path)

    def __selectNodes(self):
        if hou.selectedNodes():
            self.sel_nodes = hou.selectedNodes()
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
                        # This is a sequence.
                        self.__copySeq(parm)
                    elif "UDIM" in parm.unexpandedString():
                        # This is UDIM.
                        self.__copyUDIM(parm)
                    else:
                        # This is a file
                        self.__copyFile(parm)

    def __copyFile(self, parm):
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
        rename_status = 1
        self.makeFolder(new_dir)
        # copy
        if self.__checkExistance(old_path):
            if not self.__checkExistance(new_path):
                if self.changes_accept:
                    shutil.copy(old_path, new_path)
                self.__saveLog(data)
            else:
                print "This file is already exist in destination folder: %s" % parm.path()
                rename_status = 0
        else:
            print "This file doesn't exist: %s" % parm.path()
            rename_status = 0
        if rename_status:
            if self.changes_accept:
                parm.set(new_string)
        # set new parameter value

    def __copyUDIM(self, parm):
        # check type
        # copy
        # set new parameter value
        # log changes
        pass

    def __copySeq(self, parm):
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

w = HSC(collect_folder)