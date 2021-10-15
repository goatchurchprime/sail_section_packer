extends RigidBody2D

var nextrotation = 0
func _integrate_forces(state):
	if nextrotation != 0:
		var xform = state.get_transform()
		xform *= Transform2D(deg2rad(nextrotation), Vector2(0,0))
		print(xform.origin)
		state.set_transform(xform)
		nextrotation = 0
		

func loadgeometry(outercontour, innerlines):
		var lv = PoolVector2Array()
		lv.resize(len(outercontour))
		for i in range(len(outercontour)):
			lv[i] = Vector2(outercontour[i][0], outercontour[i][1])
		$Line2D.points = lv
		$Polygon2D.polygon = lv
		$CollisionPolygon2D.polygon = lv
		for innerline in innerlines:
			var liv = PoolVector2Array()
			liv.resize(len(innerline))
			for i in range(len(innerline)):
				liv[i] = Vector2(innerline[i][0], innerline[i][1])
			var innerline2d = Line2D.new()
			innerline2d.points = liv
			$innerlines.add_child(innerline2d)

func _on_sailpanel_input_event(viewport, event, shape_idx):
	if event is InputEventMouseButton and event.pressed:
		get_parent().get_parent().sailpanelmousedown(self, event.position)
