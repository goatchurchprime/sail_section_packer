extends RigidBody2D


func loadgeometry(outercontour):
		var lv = PoolVector2Array()
		lv.resize(len(outercontour))
		for i in range(len(outercontour)):
			lv[i] = Vector2(outercontour[i][0], outercontour[i][1])
		$Line2D.points = lv
		$CollisionPolygon2D.polygon = lv


func _on_sailpanel_input_event(viewport, event, shape_idx):
	if event is InputEventMouseButton and event.pressed:
		get_parent().get_parent().sailpanelmousedown(self, event.position)
