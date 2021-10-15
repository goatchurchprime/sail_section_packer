extends Node2D

var fshapes = "../dxffiles/aamaout/170color/shapes.json"
var fpositions = "../dxffiles/aamaout/170color/positions.json"

func _ready():
	var f = File.new()
	f.open(fshapes, File.READ)
	var ljs = f.get_as_text()
	var p = JSON.parse(ljs)
	var js = p.result
	for i in range(len(js)):
		var j = js[i]
		var rb = load("res://sailpanel.tscn").instance()
		rb.name = j["blockname"]
		rb.loadgeometry(j["outercontour"], j["innerlines"])
		rb.position = Vector2(1400 + ((i%3)-1)*500, -600 - 100*i)
		$sailpanels.add_child(rb)
#	[{blockname:F15-PATCH-reflY0, blockposition:[0, 0], blockrotation:0, innerlines:[[[5491.907161, 2678.335766], [5396.186497, 2650.849451]], [[5498.434904, 2706.220501], [5384.12733, 2673.39693]], [[5471.225459, 2663.404504], [5471.029685, 2664.640572], [5470.461527, 2665.755646], [5469.5766, 2666.640572], [5468.461527, 2667.208731], [5467.225459, 2667.404504], [5465.989391, 2667.208731], [5464.874318, 2666.640572], [5463.989391, 2665.755646], [5463.421233, 2664.640572], [5463.225459, 2663.404504], [5463.421233, 2662.16843

var sailpaneldragging = null
var sailpaneldraggingmode = RigidBody2D.MODE_CHARACTER
var mousedownposition = Vector2(0,0)
var sailpaneldownposition = Vector2(0, 0)
var mouseposition = Vector2(0,0)
var mousedown = false

func sailpanelmousedown(sailpanel, lmousedownposition):
	if sailpaneldragging == null:
		sailpaneldragging = sailpanel
		mousedownposition = lmousedownposition
		sailpaneldownposition = sailpaneldragging.position
		sailpaneldraggingmode = sailpaneldragging.mode
		sailpaneldragging.mode = RigidBody2D.MODE_CHARACTER
		print(sailpanel.name, " ", "dragging ", sailpanel.name)
		mousedown = true

func _physics_process(delta):
	if sailpaneldragging != null:
		if mousedown:
			var destinationposition = sailpaneldownposition + (mouseposition - mousedownposition)*$Camera2D.zoom
			var dirvec = destinationposition - sailpaneldragging.position
			if dirvec.length() > 300:
				sailpaneldragging.linear_velocity = dirvec.normalized() * 1300
			else:
				sailpaneldragging.linear_velocity = dirvec
		else:
			if sailpaneldragging != null:
				print(sailpaneldragging.name, " ", "stop dragging ")
				sailpaneldragging.mode = sailpaneldraggingmode
			sailpaneldragging = null

func _input(event):
	if event is InputEventMouseMotion:
		mouseposition = event.position
	elif event is InputEventMouseButton:
		if event.button_index == BUTTON_LEFT:
			mousedown = event.pressed
		elif event.pressed and (event.button_index == BUTTON_WHEEL_UP or event.button_index == BUTTON_WHEEL_DOWN):
			var cp = event.position - get_viewport().size/2
			var mp = cp*$Camera2D.zoom + $Camera2D.offset
			$Camera2D.zoom = $Camera2D.zoom/1.5 if event.button_index == BUTTON_WHEEL_UP else $Camera2D.zoom*1.5
			$Camera2D.offset = mp - cp*$Camera2D.zoom
	elif event is InputEventKey and event.pressed:
		if sailpaneldragging != null:
			if event.scancode == KEY_S:
				sailpaneldraggingmode = RigidBody2D.MODE_STATIC
				sailpaneldragging.get_node("Polygon2D").color = Color.darkred
			elif event.scancode == KEY_C:
				sailpaneldraggingmode = RigidBody2D.MODE_CHARACTER
				sailpaneldragging.get_node("Polygon2D").color = Color.teal
			elif event.scancode == KEY_R:
				sailpaneldragging.nextrotation += 90


func _on_SavePositions_button_down():
	var sailpanelpositions = { }
	for sailpanel in $sailpanels.get_children():
		sailpanelpositions[sailpanel.name] = [sailpanel.position.x, sailpanel.position.y, sailpanel.rotation_degrees] 
	print("saving %d positions"%len(sailpanelpositions))
	var f = File.new()
	f.open(fpositions, File.WRITE)
	f.store_string(JSON.print(sailpanelpositions))
	f.close()
