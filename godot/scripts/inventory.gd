extends RefCounted
## Inventar mit Gewichtslimit. Gleiche Gegenstände werden gestapelt,
## Ausrüstungsstücke (mit eigenen Werten) liegen einzeln in `gear`.

signal changed

var capacity := 100.0
var items: Dictionary = {} # item_id -> Anzahl
var gear: Array[Dictionary] = [] # einzelne Ausrüstungsstücke, siehe Game.roll_gear
var weight_factors: Dictionary = {} # Kategorie -> Faktor (z. B. "Erz": 0.8 durch Stärke-Schwellen)


func item_weight(id: String) -> float:
	var def := Game.item(id)
	return float(def.get("weight", 0.0)) * float(weight_factors.get(def.get("category", ""), 1.0))


func weight() -> float:
	var total := 0.0
	for id in items:
		total += item_weight(id) * int(items[id])
	for g in gear:
		total += item_weight(g["id"])
	return total


func count(id: String) -> int:
	return int(items.get(id, 0))


## Wie viele Stück von `id` noch in die Tasche passen.
func space_for(id: String) -> int:
	var w := item_weight(id)
	if w <= 0.0:
		return 1_000_000
	return int(floor((capacity - weight()) / w + 0.0001))


## Fügt bis zu `amount` Stück hinzu und gibt zurück, wie viele tatsächlich hineinpassten.
func add(id: String, amount: int) -> int:
	var added := mini(amount, space_for(id))
	if added <= 0:
		return 0
	items[id] = count(id) + added
	changed.emit()
	return added


func remove(id: String, amount: int) -> int:
	var removed := mini(amount, count(id))
	if removed <= 0:
		return 0
	if removed == count(id):
		items.erase(id)
	else:
		items[id] = count(id) - removed
	changed.emit()
	return removed


func has_all(ingredients: Dictionary, multiplier := 1) -> bool:
	for id in ingredients:
		if count(id) < int(ingredients[id]) * multiplier:
			return false
	return true


func add_gear(g: Dictionary) -> bool:
	if space_for_gear(g["id"]) <= 0:
		return false
	gear.append(g)
	changed.emit()
	return true


func space_for_gear(id: String) -> int:
	return 1 if weight() + item_weight(id) <= capacity + 0.0001 else 0


func take_gear(uid: int) -> Dictionary:
	for i in gear.size():
		if int(gear[i]["uid"]) == uid:
			var g := gear[i]
			gear.remove_at(i)
			changed.emit()
			return g
	return {}
