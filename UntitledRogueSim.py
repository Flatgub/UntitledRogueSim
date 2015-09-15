import libtcodpy as libtcod
from time import sleep

# CONSTANT DEFINITIONS #
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
MAP_WIDTH = 80
MAP_HEIGHT = 43

GUI_BOTTOM_HEIGHT = 7
GUI_SIDE_WIDTH = 15
GUI_BOTTOM_Y = SCREEN_HEIGHT - GUI_BOTTOM_HEIGHT

#GRASS_COLOUR = libtcod.darkest_green-libtcod.darkest_grey
GRASS_BGCOLOUR = libtcod.darkest_green*0.25
GRASS_FGCOLOUR = libtcod.darkest_green
FLOOR_BGCOLOUR = libtcod.sepia
FLOOR_FGCOLOUR = libtcod.sepia*0.70

POPUP_DEFAULT_BACK = libtcod.white
POPUP_DEFAULT_FRONT = libtcod.black

#FOV_ALGO = libtcod.FOV_PERMISSIVE_3
FOV_ALGO = libtcod.FOV_DIAMOND
VISION_RADIUS = 50
UNSEEN_TERRAIN_DARKNESS = 0.25

#PATHFINDING STUFF
DIAGONAL_COST = 1.41
ASSUMED_PASSABLE_TILES = ['Door']

GameIsRunning = True


newidentifier = 0

###############
##	Classes	 ##
###############

## Entity Related Classes
class Entity:
	def __init__(self,name, x, y , char, colour, flags = []):
		global newidentifier
		self.id = newidentifier
		newidentifier += 1
		self.name = name
		print(self.name + ' has ID ' + str(self.id))
		self.x = x
		self.y = y
		self.char = char
		self.colour = colour
		self.flags = flags
		

	def Move(self, nx, ny):
		Tile = Map[self.x+nx][self.y+ny]
		if not 'Impassable' in Tile.flags:
			if 'CanSee' in self.flags:
				self.Vision.RecomputeFOV()
			self.x += nx
			self.y += ny
			if 'CanSee' in self.flags:
				self.Vision.RecomputeFOV()
		else:
			print('Failed to move')

	def Draw(self):
		if CanTileBeSeenByPlayer(self.x,self.y):
			libtcod.console_set_default_foreground(MainConsole, self.colour)
			libtcod.console_put_char(MainConsole, self.x, self.y, self.char, libtcod.BKGND_NONE)

	def Clear(self):
		libtcod.console_put_char(MainConsole,self.x,self.y,Map[self.x][self.y].char,libtcod.BKGND_NONE)

class PersonComponent:
	def __init__(self,owner,flags = []):
		self.owner = owner
		self.flags = flags

	def Interact(self, nx, ny):
		targettile = Map[self.owner.x+nx][self.owner.y+ny]
		if 'Interactable' in targettile.flags:
			targettile.Interact()

class VisionComponent:
	def __init__(self,owner, maxviewrange):
		self.owner = owner
		self.maxviewrange = maxviewrange
		self.fovmap = libtcod.map_new(MAP_WIDTH,MAP_HEIGHT)
		self.viewmodifier = 1
		for y in range(MAP_HEIGHT):
			for x in range(MAP_WIDTH):
				scannedtile = Map[x][y]
				if 'ViewBlocking' in scannedtile.flags:
					canseethrough = False
				else:
					canseethrough = True
				if "Impassable" in scannedtile.flags:
					canwalkthrough = False
				else:
					canwalkthrough = True
				libtcod.map_set_properties(self.fovmap,x,y,canseethrough,canwalkthrough)
		self.owner.flags.append('CanSee')
				
	def RecomputeFOV(self):
		viewrange = self.maxviewrange * self.viewmodifier
		libtcod.map_compute_fov(self.fovmap,self.owner.x,self.owner.y,viewrange,True,FOV_ALGO)
		if hasattr(self.owner,'Pathfinding'):
			for y in range(MAP_HEIGHT):
				for x in range(MAP_WIDTH):
					if	self.CanSee(x,y):
						scannedtile = Map[x][y]
						if 'ViewBlocking' in scannedtile.flags:
							canseethrough = False
						else:
							canseethrough = True
						if "Impassable" in scannedtile.flags and not scannedtile.name in ASSUMED_PASSABLE_TILES:
							canwalkthrough = False
						else:
							canwalkthrough = True
						libtcod.map_set_properties(self.owner.Pathfinding.navmap,x,y,canseethrough,canwalkthrough)
		
	def CanSee(self,x,y):
		visible = libtcod.map_is_in_fov(self.fovmap, x, y)
		return visible

class PathfindingComponent:
	def __init__(self,owner,flags=[]):
		self.owner = owner
		self.flags = flags
		self.navmap = libtcod.map_new(MAP_WIDTH,MAP_HEIGHT)
		self.currentpath = None
		self.currenttarget = None
		self.currentlyonpath = False
		
	def BuildNavMap(self):
		numberofdoors = 0
		for y in range(MAP_HEIGHT):
			for x in range(MAP_WIDTH):
				scannedtile = Map[x][y]
				if 'ViewBlocking' in scannedtile.flags:
					canseethrough = False
				else:
					canseethrough = True
				if scannedtile.name == 'Door':
					numberofdoors += 1
				if "Impassable" in scannedtile.flags and not scannedtile.name in ASSUMED_PASSABLE_TILES:
					canwalkthrough = False
				else:
					canwalkthrough = True
				libtcod.map_set_properties(self.navmap,x,y,canseethrough,canwalkthrough)
		del self.currentpath
		print('Finished Building Navmap:')
		print('Number of doors found: ' + str(numberofdoors))
		self.currentpath = libtcod.dijkstra_new(self.navmap,DIAGONAL_COST)
		self.UpdateNavMapLocation()
		
	def BuildNavMapEmpty(self):
		for y in range(MAP_HEIGHT):
			for x in range(MAP_WIDTH):
				libtcod.map_set_properties(self.navmap,x,y,True,True)
		del self.currentpath
		print('Finished creating blank NavMap for ' + self.owner.name)
		self.currentpath = libtcod.dijkstra_new(self.navmap,DIAGONAL_COST)
		self.UpdateNavMapLocation()
				
	def UpdateNavMapLocation(self):
		libtcod.dijkstra_compute(self.currentpath, self.owner.x, self.owner.y)
		
	def RecomputePath(self):
		self.UpdateNavMapLocation()
		err = libtcod.dijkstra_path_set(self.currentpath, self.currenttarget.x, self.currenttarget.y)
		if err == False:
			print(self.owner.name + ' failed to recompute path')
			self.currentlyonpath = False
			self.currentpath = None
			return err
		else:
			self.currentlyonpath = True
			return True
		
	def SetCurrentTarget(self,target):
		self.currenttarget = target
		print(self.owner.name + '\'s current target is now ' + target.name)
			
	def ReturnNextPointOnPath(self,offset):
		if self.currentlyonpath == True:
			if not libtcod.dijkstra_is_empty(self.currentpath):
				if offset == True:
					err = libtcod.dijkstra_get(self.currentpath, 1)
					if not err == None:
						x,y = libtcod.dijkstra_get(self.currentpath, 0)
						x = x - self.owner.x
						y = y - self.owner.y							
						return x,y
				else:
					x,y = libtcod.dijkstra_get(self.currentpath, 0)
					if not x == False:
						return x,y
				print('Unable to get next spot in path')
				return None, None
			else:
				print('Path is empty')
				#self.SetCurrentTarget(CreateRandomWalkableCoords())
				self.RecomputePath()
				return None, None
		else:
			print('Not on path')
			return None, None
	
	def SuccessfullyMovedToNextPoint(self):
		libtcod.dijkstra_path_walk(self.currentpath)
		self.RecomputePath()

	def FailedToMoveToNextPoint(self):
		self.RecomputePath()
		
	def DrawPath(self,console):
		if self.currentpath != None:
			for i in range(0,libtcod.dijkstra_size(self.currentpath)):
				if not i == libtcod.dijkstra_size(self.currentpath)-1:
					x,y = libtcod.dijkstra_get(self.currentpath,i)
					libtcod.console_set_default_background(console,libtcod.yellow)
					libtcod.console_put_char(console, x, y, '=', libtcod.BKGND_SET)
				else:
					x,y = libtcod.dijkstra_get(self.currentpath,i)
					libtcod.console_set_char_background(console, x, y, libtcod.blue,libtcod.BKGND_SET)
					
class AIComponent:
	def __init__(self,owner,flags=['Conscious']):
		self.owner = owner
		self.flags = flags
		self.state = 'LookingForTarget'
		self.knownpeopledict = {}
		self.currentgoal = ["Nothing",None]
		
	def MoveAlongCurrentPath(self):
		if 'Conscious' in self.flags:
			x,y = self.owner.Pathfinding.ReturnNextPointOnPath(False)
			if not x == None:
				ox,oy = self.owner.Pathfinding.ReturnNextPointOnPath(True)
				if not 'Impassable' in Map[x][y].flags:
					self.owner.Move(ox,oy)
					self.owner.Pathfinding.SuccessfullyMovedToNextPoint()
				else:
					if Map[x][y].name == 'Door':
						print(self.owner.name + ' has found a door')
						opened = Map[x][y].InteractWithPartUsingChoice('DoorPart','Open')
						print(self.owner.name + ' Tried to open the door')
						if opened == False:
							libtcod.map_set_properties(self.owner.Pathfinding.navmap,x,y,False,False)
							print(self.owner.name + ' thinks that door at ' + str(x) + ',' + str(y) + ' is locked')
						else:
							print(self.owner.name + ' succesfully opened the door')
					self.owner.Pathfinding.FailedToMoveToNextPoint()
	
	def FollowTarget(self,target = 'Undefined'):
		if target == 'Undefined':
			target = self.owner.Pathfinding.currenttarget
		if target == None:
			print(self.owner.name + ' has no target to follow')
		elif not isinstance(target,Coord):
			targetcanbeseen = False
			if hasattr(self.owner,'Vision'):
				targetcanbeseen = self.owner.Vision.CanSee(target.x,target.y)
			if targetcanbeseen and self.owner.Pathfinding.currenttarget == target:
				pass
			elif targetcanbeseen and self.owner.Pathfinding.currenttarget != target:
				self.owner.Pathfinding.SetCurrentTarget(target)
			elif not targetcanbeseen and self.owner.Pathfinding.currenttarget == target:
				self.owner.Pathfinding.SetCurrentTarget(Coord(target.x,target.y,'Last seen location for ' + target.name))
			elif not targetcanbeseen and self.owner.Pathfinding.currenttarget != target:
				print (self.owner.name + ' can not see their target')
				self.state = 'Idle'
				
		
		self.MoveAlongCurrentPath()
	
	def GetListOfVisiblePeople(self):
		visiblepeople = []
		if hasattr(self.owner,'Vision'):
			for ent in ActiveEntityList:
				if self.owner.Vision.CanSee(ent.x,ent.y) and hasattr(ent,'Person'):
					visiblepeople.append(ent)
		return visiblepeople
						
	def AddNewPeopleToKnowledge(self):
		visiblepeople = self.GetListOfVisiblePeople()
		for ent in visiblepeople:
			if not self.knownpeopledict.__contains__(ent.id):
				print('Adding ' + ent.name + ' to ' + self.owner.name + '\'s knowledge')
				details = {'Name':ent.name,
				           'LastX':ent.x,
						   'LastY':ent.y}
				self.knownpeopledict.update({ent.id:details})
	
	def UpdateKnowledge(self):
		visiblepeople = self.GetListOfVisiblePeople()
		self.AddNewPeopleToKnowledge()
		for ent in visiblepeople:
			if self.knownpeopledict.__contains__(ent.id):
				print(self.owner.name + " has updated their knowledge of " + ent.name)
				details = {'Name':ent.name,
						   'LastX':ent.x,
						   'LastY':ent.y}
				self.knownpeopledict.update({ent.id:details})
				
	def ActCurrentState(self):
		#self.AddNewPeopleToKnowledge()
		if self.state == 'Idle':
			print(self.owner.name + ' Is Idle')
			pass
		elif self.state == 'Following':
			print(self.owner.name + ' is following')
			self.FollowTarget()
		elif self.state == 'LookingForTarget':
			print(self.owner.name + ' is looking for target')
			if self.owner.Pathfinding.currenttarget != None:
				target = self.owner.Pathfinding.currenttarget
				if self.owner.Vision.CanSee(target.x,target.y):
					self.state = 'Following'
					self.FollowTarget(target)
	
	#def ActCurrentGoal(self):
	#	if self.currentgoal[0] == "Follow"
	
	def ActGeneral(self):
		self.UpdateKnowledge()
		self.ActCurrentState()
	
## Terrain Related Classes	
class Terrain:
	def __init__(self,x,y,name, char, bgcolour, fgcolour, flags = [], args = []):
		self.x = x
		self.y = y
		self.name = name
		self.char = char
		self.bgcolour = bgcolour
		self.fgcolour = fgcolour
		self.flags = flags
		self.args = args

	def InteractWithPartUsingChoice(self,part,choice):
		if part == 'DoorPart':
			return self.Door.InteractUsingChoice(choice)
			UpdateFOVtile(self.x,self.y)
	
	def InteractByPlayer(self):
		if 'IsDoor' in self.flags:
			self.Door.InteractByPlayer()
			UpdateFOVtile(self.x,self.y)

class DoorComponent:
	def __init__(self,owner, openchar, closedchar,state,flags,toggleflags):
		self.owner = owner
		self.openchar = openchar
		self.closedchar = closedchar
		self.state = state
		self.flags = flags
		self.toggleflags = toggleflags

	def InteractUsingChoice(self,choice):
		if choice == 'Open':
			if self.state != 'Locked':
				for pair in self.toggleflags:
					ReplaceInList(self.owner.flags,pair[0],pair[1])
				self.owner.char = self.openchar
				self.state = 'Open'
				return True
			else:
				return False
		elif choice == 'Close':
			if IsTileEmpty(self.owner.x,self.owner.y):
				for pair in self.toggleflags:
					ReplaceInList(self.owner.flags,pair[1],pair[0])
				self.owner.char = self.closedchar
				self.state = 'Closed'
				return True
			else:
				return False
	
	def InteractByPlayer(self):
		choices = []
		# Define which choices are available
		if self.state == 'Closed':
			choices.append('Open')
			if 'Lockable' in self.flags:
				choices.append('Lock')
		elif self.state == 'Open':
			choices.append("Close")

		if self.state == 'Locked':
			choices.append('Unlock')
		
		# Let the player choose
		key = libtcod.console_wait_for_keypress(True)
		choice = PopupChoicesMenu('How do you want to interact?',choices,True)
		if not choice == None:
			if choice == 'Open':
				for pair in self.toggleflags:
					ReplaceInList(self.owner.flags,pair[0],pair[1])
				self.owner.char = self.openchar
				self.state = 'Open'
			elif choice == 'Close':
				if IsTileEmpty(self.owner.x,self.owner.y):
					for pair in self.toggleflags:
						ReplaceInList(self.owner.flags,pair[1],pair[0])
					self.owner.char = self.closedchar
					self.state = 'Closed'
			elif choice == 'Lock':
				self.state = 'Locked'
			elif choice == 'Unlock':
				self.state = 'Closed'
					
				
## Misc. Classes			
class Rect:
	def __init__(self,x,y,w,h):
		self.x1 = x
		self.y1 = y
		self.x2 = x + w
		self.y2 = y + h

class Coord:
	def __init__(self,x,y,name = 'unnamed set of coords'):
		self.x = x
		self.y = y
		self.name = name


##################
##	Functions	##
##################

def ConstructTemplateTerrain(request,x,y):
	GrassChars = ['.',',','`','\'']
	TreeChars = [6,5]
	if request == 'Grass':
		return Terrain(x,y,'Grass',GrassChars[libtcod.random_get_int(0,0,3)],GRASS_BGCOLOUR,GRASS_FGCOLOUR,['Passable','NonViewBlocking'])
	if request == 'Wall':
		return Terrain(x,y,'Wall','#',libtcod.dark_gray,libtcod.gray,['Impassable','ViewBlocking'])
	if request == 'Tree':
		return Terrain(x,y,'Tree',TreeChars[libtcod.random_get_int(0,0,1)],GRASS_BGCOLOUR,libtcod.green,['Impassable','ViewBlocking'])
	if request == 'Floor':
		return Terrain(x,y,'Floor','_',FLOOR_BGCOLOUR,FLOOR_FGCOLOUR,['Passable','NonViewBlocking',"CoveredByRoof"])
	if request == 'Door':
		newdoor = Terrain(x,y,'Door',179,FLOOR_FGCOLOUR,FLOOR_BGCOLOUR,['Impassable','ViewBlocking','IsDoor','Interactable',"CoveredByRoof"])
		newdoor.Door = DoorComponent(newdoor,186,179,'Closed',['Lockable'],[ ['Impassable','Passable'],['ViewBlocking','NonViewBlocking'] ])
		return newdoor

def BuildRoom(room):
	global Map

	#Build the walls
	for x in range(room.x1,room.x2+1):
		Map[x][room.y1] = ConstructTemplateTerrain('Wall',x,room.y1)
	for x in range(room.x1 + 1,room.x2+1):
		Map[x][room.y2] = ConstructTemplateTerrain('Wall',x,room.y2)
	for y in range(room.y1 + 1,room.y2+1):
		Map[room.x1][y] = ConstructTemplateTerrain('Wall',room.x1,y)
	for y in range(room.y1 + 1,room.y2+1):
		Map[room.x2][y] = ConstructTemplateTerrain('Wall',room.x2,y)

	side = libtcod.random_get_int(0,1,4)
	if side == 1:
		x = room.x1+(room.x2-room.x1)/2
		Map[x][room.y1] = ConstructTemplateTerrain('Door',x,room.y1)
	if side == 2:
		y = room.y1+(room.y2-room.y1)/2
		Map[room.x1][y] = ConstructTemplateTerrain('Door',room.x1,y)
	if side == 3:
		x = room.x1+(room.x2-room.x1)/2
		Map[x][room.y2] = ConstructTemplateTerrain('Door',x,room.y2)
	if side == 4:
		y = room.y1+(room.y2-room.y1)/2
		Map[room.x2][y] = ConstructTemplateTerrain('Door',room.x2,y)


	#Build the floor
	for x in range(room.x1+1,room.x2):
		for y in range(room.y1+1,room.y2):
			Map[x][y] = ConstructTemplateTerrain('Floor',x,y)

def MakeMap():
	global Map
	Map = [[ ConstructTemplateTerrain('Grass',x,y)
		for y in range(MAP_HEIGHT) ]
			for x in range(MAP_WIDTH) ]

	room1 = Rect(libtcod.random_get_int(0,5,MAP_WIDTH-6),libtcod.random_get_int(0,5,MAP_HEIGHT-6),5,5)
	room2 = Rect(libtcod.random_get_int(0,5,MAP_WIDTH-7),libtcod.random_get_int(0,5,MAP_HEIGHT-7),6,6)
	room3 = Rect(libtcod.random_get_int(0,5,MAP_WIDTH-10),libtcod.random_get_int(0,5,MAP_HEIGHT-19),9,9)
	BuildRoom(room1)
	BuildRoom(room2)
	BuildRoom(room3)
	for x in range(MAP_WIDTH):
		for y in range(MAP_HEIGHT):
			if Map[x][y].name == 'Grass':
				chance = libtcod.random_get_int(0,0,100)
				if chance <= 2:
					Map[x][y] = ConstructTemplateTerrain('Tree',x,y)
						
def HandlePlayerInput():
	global ActiveObjectsList, Key
	playeraction = 'did-nothing'

	if Key.vk == libtcod.KEY_UP:
		for ent in ActiveEntityList:
			if 'ControlledByPlayer' in ent.flags:
				ent.Move(0,-1)
		playeraction = 'Moved'
				
	elif Key.vk == libtcod.KEY_DOWN:
		for ent in ActiveEntityList:
			if 'ControlledByPlayer' in ent.flags:
				ent.Move(0,1)
		playeraction = 'Moved'
	
	elif Key.vk == libtcod.KEY_LEFT:
		for ent in ActiveEntityList:
			if 'ControlledByPlayer' in ent.flags:
				ent.Move(-1,0)
		playeraction = 'Moved'
				
	elif Key.vk == libtcod.KEY_RIGHT:
		for ent in ActiveEntityList:
			if 'ControlledByPlayer' in ent.flags:
				ent.Move(1,0)
		playeraction = 'Moved'
		
	elif Key.vk == libtcod.KEY_SPACE:
		playeraction = 'Waited'

	elif Key.vk == libtcod.KEY_ENTER and Key.lalt:
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

	elif Key.vk == libtcod.KEY_ESCAPE:
		ExitGame()

	else:
		#Key = libtcod.console_wait_for_keypress(True)
		key_char = chr(Key.c)
		if key_char == 'e':
			for ent in ActiveEntityList:
				if 'ControlledByPlayer' in ent.flags:
					Menu_InteractWith(ent.x,ent.y)
					if 'CanSee' in ent.flags:
						ent.Vision.RecomputeFOV()
	
	return playeraction

def Menu_InteractWith(x,y):
	interactables = GetSurroundingInteractable(x,y)
	intnames = []
	for item in interactables:
		intnames.append(item.name)

	choice = PopupChoicesMenu('Interact with what?', intnames)
	if not choice == None:
		interactables[choice].InteractByPlayer()

def PopupChoicesMenu(header, options, returnchoice = False):
	if len(options) > 26: raise ValueError('Cannot have a menue with more than 26 options.')

	allstrings = list(options)
	allstrings.append(header)
	width = GetLengthOfLongestInList(allstrings)
	#calculate the total height for the header (after auto-wrap) and one line per option
	header_height = libtcod.console_get_height_rect(MainConsole, 0, 0, width, SCREEN_HEIGHT, header)
	if header == '':
		header_height = 0
	height = len(options) + header_height + 3
	
	consolewidth = width+4
	consoleheight = height+4
	
	
		
	#create an off screen console that represents the menu's window
	PopupConsole = libtcod.console_new(consolewidth, consoleheight)
	
	libtcod.console_set_default_foreground(PopupConsole,POPUP_DEFAULT_FRONT)
	libtcod.console_set_default_background(PopupConsole,POPUP_DEFAULT_BACK)
	libtcod.console_clear(PopupConsole)
	for x in range(consolewidth):
		libtcod.console_put_char(PopupConsole,x, 0,205,libtcod.BKGND_NONE)
		libtcod.console_put_char(PopupConsole,x, consoleheight-1,205,libtcod.BKGND_NONE)
		
	for y in range(consolewidth):
		libtcod.console_put_char(PopupConsole,0, y,186 ,libtcod.BKGND_NONE)
		libtcod.console_put_char(PopupConsole,consolewidth-1, y,186 ,libtcod.BKGND_NONE)
		
	libtcod.console_put_char(PopupConsole,0,0,201 ,libtcod.BKGND_NONE)
	libtcod.console_put_char(PopupConsole,0, consoleheight-1,200 ,libtcod.BKGND_NONE)
	libtcod.console_put_char(PopupConsole,consolewidth-1, 0,187 ,libtcod.BKGND_NONE)
	libtcod.console_put_char(PopupConsole,consolewidth-1, consoleheight-1,188 ,libtcod.BKGND_NONE)
	
	
	#print the header with auto-wrap
	libtcod.console_set_default_foreground(PopupConsole,POPUP_DEFAULT_FRONT)
	libtcod.console_print_rect_ex(PopupConsole, 2, 2, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
	libtcod.console_print_ex(PopupConsole, 2, height+1, libtcod.BKGND_NONE, libtcod.LEFT, "Esc to cancel")

	#print all the options
	y = header_height+3
	letter_index = ord('a')
	for option_text in options:
		text = chr(letter_index) + ') ' + option_text
		libtcod.console_print_ex(PopupConsole, 2, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
		y += 1
		letter_index += 1

	#blit the contents of "window" to the root console
	x = SCREEN_WIDTH/2 - width/2
	y = SCREEN_HEIGHT/2 - height/2
	libtcod.console_blit(PopupConsole, 0, 0, consolewidth, consoleheight, 0, x, y, 1.0, 1)

	#present the root console to the player and wait for a response
	libtcod.console_flush()
	key = libtcod.console_wait_for_keypress(True)
	#convert the ASCII code to an index, if it corresponds to an option, return it
	index = key.c - ord('a')
	
	while index < 0 or index >= len(options):
		key = libtcod.console_wait_for_keypress(True)
		index = key.c - ord('a')
		if key.vk == libtcod.KEY_ESCAPE:
			return None
		
	if returnchoice == True:
		return options[index]
	else:
		return index
	
def CanPlayerBeSeen():
	player = None
	for ent in ActiveEntityList:
		if 'ControlledByPlayer' in ent.flags:
			player = ent
			break
	
	x = player.x
	y = player.y
	playercanbeseen = False
	for ent in ActiveEntityList:
		if 'CanSee' in ent.flags and not 'ControlledByPlayer' in ent.flags:
			if ent.Vision.CanSee(x,y) == True:
				playercanbeseen = True
				break
	return playercanbeseen
	
def CanTileBeSeen(x,y):
	tilecanbeseen = False
	for ent in ActiveEntityList:
		if 'CanSee' in ent.flags and not 'ControlledByPlayer' in ent.flags:
			if ent.Vision.CanSee(x,y) == True:
				tilecanbeseen = True
				break
	return tilecanbeseen
	
def CanTileBeSeenByPlayer(x,y):
	tilecanbeseen = False
	for ent in ActiveEntityList:
		if 'CanSee' in ent.flags and 'ControlledByPlayer' in ent.flags:
			if ent.Vision.CanSee(x,y) == True:
				tilecanbeseen = True
				break
	return tilecanbeseen
			
def IsPlayerInside():
	player = None
	for ent in ActiveEntityList:
		if 'ControlledByPlayer' in ent.flags:
			player = ent
			break
	
	x = player.x
	y = player.y
	playerisinside = False
	if 'CoveredByRoof' in Map[x][y].flags:
		playerisinside = True
	return playerisinside

def RenderGui():
	libtcod.console_set_default_foreground(GUIBottomConsole,libtcod.white)
	libtcod.console_set_default_background(GUIBottomConsole,libtcod.black)
	libtcod.console_clear(GUIBottomConsole)
	for x in range(MAP_WIDTH):
		libtcod.console_put_char(GUIBottomConsole,x, 0,205,libtcod.BKGND_NONE)
		
	if CanPlayerBeSeen():
		libtcod.console_print_ex(GUIBottomConsole,3, 2, libtcod.BKGND_NONE, libtcod.LEFT, "VISIBLE")
	else:
		libtcod.console_print_ex(GUIBottomConsole,3, 2, libtcod.BKGND_NONE, libtcod.LEFT, "HIDDEN")
	
	if IsPlayerInside():
		libtcod.console_print_ex(GUIBottomConsole,3, 4, libtcod.BKGND_NONE, libtcod.LEFT, "INSIDE")
	else:
		libtcod.console_print_ex(GUIBottomConsole,3, 4, libtcod.BKGND_NONE, libtcod.LEFT, "OUTSIDE")

#############################################		 
def RenderEverything():
	player = None
	for ent in ActiveEntityList:
		if 'ControlledByPlayer' and 'CanSee' in ent.flags:
				player = ent
				break			
	#player = TestDummy
			
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			terraintile = Map[x][y]
			if player != None:
				canseetile = player.Vision.CanSee(x,y)
				
			if canseetile:
				libtcod.console_set_char_background(MainConsole,x,y,terraintile.bgcolour,libtcod.BKGND_SET)
				libtcod.console_set_default_foreground(MainConsole,terraintile.fgcolour)
				libtcod.console_put_char(MainConsole, x, y, terraintile.char, libtcod.BKGND_NONE)
			else:
				libtcod.console_set_char_background(MainConsole,x,y,terraintile.bgcolour*UNSEEN_TERRAIN_DARKNESS,libtcod.BKGND_SET)
				libtcod.console_set_default_foreground(MainConsole,terraintile.fgcolour*UNSEEN_TERRAIN_DARKNESS)
				libtcod.console_put_char(MainConsole, x, y, terraintile.char, libtcod.BKGND_NONE)

	for ent in ActiveEntityList:
		ent.Draw()

	#DrawAllPaths(MainConsole)
	RenderGui()
	libtcod.console_blit(MainConsole, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
	libtcod.console_blit(GUIBottomConsole, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, GUI_BOTTOM_Y)
#############################################

def GetSurroundingInteractable(x,y):
	interactables = []
	vars = [-1,0,1]
	for ox in vars:
		for oy in vars:
			if ox == 0 and oy == 0:
				continue
			scannedtile = Map[x+ox][y+oy]
			if 'Interactable' in scannedtile.flags:
				interactables.append(scannedtile)
	return interactables

def GetLengthOfLongestInList(list):
	longestleng = 0
	for item in list:
		if len(item) > longestleng:
			longestleng = len(item)
	return longestleng
		
def ExitGame():
	global GameIsRunning
	GameIsRunning = False

def GetInput():
	global Mouse, Key
	Mouse = libtcod.Mouse()
	Key = libtcod.Key()

def InitFOVMaps():
	for ent in ActiveEntityList:
		if 'CanSee' in ent.flags:
			ent.Vision.RecomputeFOV()
			
def InitNavMaps():
	for ent in ActiveEntityList:
		if hasattr(ent,'Pathfinding'):
			ent.Pathfinding.BuildNavMapEmpty()
			ent.Pathfinding.RecomputePath()
			if hasattr(ent,'Vision'):
				ent.Vision.RecomputeFOV()

def IsTileWalkable(x,y):
	return 'Passable' in Map[x][y].flags

def IsTileEmpty(x,y):
	tilefree = True
	for ent in ActiveEntityList:
		if ent.x == x and ent.y == y:
			tilefree = False
			break
	return tilefree
	
def GetEntitiyNamesAtTile(x,y):
	names = []
	for ent in ActiveEntitiyList:
		if ent.x -- x and ent.y == y:
			names.appent(ent.name)
	return names
	
def DoAllAI():
	for ent in ActiveEntityList:
		if hasattr(ent,'AI'):
			ent.AI.ActGeneral()
			
def DrawAllPaths():
	for ent in ActiveEntityList:
		if hasattr(ent,'Pathfinding'):
			ent.Pathfinding.DrawPath()
	
def UpdateFOVmap():
	for ent in ActiveEntityList:
		if 'CanSee' in ent.flags:
			for y in range(MAP_HEIGHT):
				for x in range(MAP_WIDTH):
					scannedtile = Map[x][y]
					if 'ViewBlocking' in scannedtile.flags:
						canseethrough = False
					else:
						canseethrough = True
					if "Impassable" in scannedtile.flags:
						canwalkthrough = False
					else:
						canwalkthrough = True
					libtcod.map_set_properties(ent.Vision.fovmap,x,y,canseethrough,canwalkthrough)
	
def UpdateFOVtile(x,y):
	scannedtile = Map[x][y]
	if 'ViewBlocking' in scannedtile.flags:
		canseethrough = False
	else:
		canseethrough = True
	if "Impassable" in scannedtile.flags:
		canwalkthrough = False
	else:
		canwalkthrough = True
	for ent in ActiveEntityList:
		if 'CanSee' in ent.flags:
			#if ent.Vision.CanSee(x,y):
			libtcod.map_set_properties(ent.Vision.fovmap,x,y,canseethrough,canwalkthrough)

def RecomputeAllFOV():
	for ent in ActiveEntityList:
		if 'CanSee' in ent.flags:
			ent.Vision.RecomputeFOV()
	
def ListsOverlap(source,target):
	for item in source:
		if str(item) in target:
			return True
			break
	return False
	
def ReplaceInList(list,findwhat,replacewith):
	if findwhat in list:
		list.remove(findwhat)
		list.append(replacewith)
	
def CreateRandomWalkableCoords():
	x = libtcod.random_get_int(0,0,MAP_WIDTH-1)
	y = libtcod.random_get_int(0,0,MAP_HEIGHT-1)
	while 'Impassable' in Map[x][y].flags:
		x = libtcod.random_get_int(0,0,MAP_WIDTH-1)
		y = libtcod.random_get_int(0,0,MAP_HEIGHT-1)
	return Coord(x,y,'Coords for ' + str(x) + ',' + str(y))
	
	
colours = [libtcod.red,libtcod.blue,libtcod.white,libtcod.pink]

def GeneratePerson():
	names = ['Bill','Bob','Baxter','Billy','Betty','Brian','Brobert','Blake','Brohan','Broseph']
	newname = names[libtcod.random_get_int(0,0,len(names)-1)]
	newcolour = colours.pop()
	newperson = Entity(newname,libtcod.random_get_int(0,0,MAP_WIDTH),libtcod.random_get_int(0,0,MAP_HEIGHT),2,newcolour, ['Alive','Person'])
	print(newname + ' is colour ' + str(newcolour))
	newperson.Person = PersonComponent(newperson)
	newperson.Vision = VisionComponent(newperson,75)
	newperson.Pathfinding = PathfindingComponent(newperson,[])
	newperson.AI = AIComponent(newperson,['Conscious'])
	newperson.Pathfinding.SetCurrentTarget(Player)
	return newperson

def DrawAllPaths(con):
	for ent in ActiveEntityList:
		if hasattr(ent,'Pathfinding'):
			ent.Pathfinding.DrawPath(con)

def GetEnt(id):
	for ent in ActiveEntityList:
		if ent.id == id:
			return ent
	return None

			
libtcod.console_set_custom_font('terminal8x8_gs_ro.png', libtcod.FONT_LAYOUT_ASCII_INROW | libtcod.FONT_TYPE_GREYSCALE)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Untitled Roguelike Sim', False)
MainConsole = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
GUIBottomConsole = libtcod.console_new(SCREEN_WIDTH, GUI_BOTTOM_HEIGHT)

libtcod.sys_set_fps(30)
MakeMap()

Player = Entity('Player',SCREEN_WIDTH/2,SCREEN_HEIGHT/2,1,libtcod.white, ['ControlledByPlayer','Alive','Person'])
Player.Person = PersonComponent(Player)
Player.Vision = VisionComponent(Player,75)
Player.Vision.RecomputeFOV()




ActiveEntityList = [Player]
ActiveEntityList.append(GeneratePerson())


GetInput()

InitFOVMaps()
RecomputeAllFOV()
InitNavMaps()
#ent.AI.MoveAlongCurrentPath() 
while GameIsRunning:
	
	libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,Key,Mouse)
	
	RenderEverything()
	DrawAllPaths(None)
	libtcod.console_flush()
	for obj in ActiveEntityList:
		obj.Clear()
	playeraction = HandlePlayerInput()
	
	if not playeraction == 'did-nothing':
		RecomputeAllFOV()
		DoAllAI()
	
	
	



