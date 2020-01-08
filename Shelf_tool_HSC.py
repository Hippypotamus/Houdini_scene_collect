import hou
shelf_cubic = hou.shelves.shelves()

if "Cubic tools" in shelf_cubic:
    shelf = hou.shelves.shelves()["Cubic tools"]
    print shelf
else:
    print "Not exist"
    shelf = hou.shelves.newShelf("cubic_tools", "Cubic tools")