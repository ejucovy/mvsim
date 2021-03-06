import datetime
from django.conf import settings
from django.http import (HttpResponseRedirect as redirect, 
                         HttpResponse,
                         HttpResponseForbidden as forbidden)
from django.views.decorators.csrf import csrf_exempt
from djangohelpers.lib import allow_http, rendered_with
from engine.logic import get_notifications
from engine import logic
from engine import display_logic
import httplib2
from main.models import Game, State, CourseSection, Configuration, UserInput
import os
import simplejson
import subprocess
import tempfile

@allow_http("GET")
def graph_download(request, game_id):
    key = request.GET['filename']

    # rudimentary sanitization - keys are timestamps, so they should be int'able
    try:
        int(key)
    except:
        raise TypeError("bad filename %s" % key)

    graph_dir = settings.MVSIM_GRAPH_OUTPUT_DIRECTORY
    path = os.path.join(graph_dir, "%s.png" % key)
    
    fp = open(path)
    try:
        data = fp.read()
    finally:
        fp.close()
    response = HttpResponse(data)
    response['Content-Disposition'] = 'attachment;filename="game_%s_graph.png"' % game_id
    return response

@csrf_exempt
@allow_http("POST")
def graph_svg(request, game_id):
    json = request.POST['json']
    json = simplejson.loads(json)
    
    output = ["""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="%s" height="%s" xml:space="preserve"><desc>Created with Raphael</desc><defs></defs>""" % ('640', '__GRAPH_HEIGHT__')]
    output.append("""<text x="%s" y="3" text-anchor="middle"
font-family="Arial" font-size="28" stroke="none" fill="#000"><tspan>
%s
</tspan></text>""" % ("320", request.POST['title'].strip()))


    output.append("""<text x="110" y="315" text-anchor="left"
font-family="Arial" font-size="18" stroke="none" fill="#000"><tspan>
X-axis: %s
</tspan></text>""" % request.POST['xAxis'].strip())

    for item in json:
        if item['type'] == "text":
            output.append("""<text x="%(x)s" y="%(y)s" text-anchor="%(text_anchor)s"
      font="%(font)s" stroke="%(stroke)s" fill="%(fill)s">
    <tspan>%(text)s</tspan>
</text>""" % {
                    'x': item['x'],
                    'y': int(item['y'] + 35),
                    'text_anchor': item.get('text-anchor', "left"),
                    'font': item['font'],
                    'stroke': item['stroke'],
                    'fill': item['fill'],
                    'text': item['text'],
                    })
        if item['type'] == "path":
            output.append("""<path fill="%(fill)s" stroke="%(stroke)s" d="%(path)s" opacity="%(opacity)s" stroke-width="%(swidth)s" transform="%(transform)s"></path>""" % {
                    'fill': item['fill'],
                    'stroke': item['stroke'],
                    'path': item['path'],
                    'opacity': item.get('opacity', 1),
                    'transform': "translate(0,35)",
                    'swidth': item.get('stroke-width', 1),
                    })
        if item['type'] == "circle":
            if not item.get('fill', "").strip():
                continue
            output.append("""<circle cx="%(cx)s" cy="%(cy)s" stroke="%(stroke)s" fill="%(fill)s" r="%(radius)s" style="opacity: %(opacity)s; stroke-width: %(swidth)s;" opacity="%(opacity)s" stroke-width="%(swidth)s"></circle>""" % {
                    'fill': item['fill'],
                    'stroke': item['stroke'],
                    'cx': item['cx'],
                    'cy': int(item['cy']) + 35,
                    'radius': item['r'],
                    'opacity': item.get('opacity', 0),
                    'swidth': item.get('stroke-width', 0),
                    })

    vars = request.POST['vars']
    vars = simplejson.loads(vars)
    y = 370
    x = 320
    for item in vars:
        var = item['text']
        color = item['color']
        opacity = item['opacity']
        output.append("""<text x="%s" y="%s" text-anchor="middle" font-size="14" font-family="Arial" font-weight="bold" stroke="none" opacity="%s" fill="%s"><tspan>%s</tspan></text>""" % (x, y, str(opacity), color, var))
        y += 20

    output.append("</svg>")
    output = '\n'.join(output)
    output = output.replace("__GRAPH_HEIGHT__", str(y)) # from the variable-legend loop above

    # POST to a microapp, git.ccnmtl.columbia.edu:svg2png.git
    # because only monty's imagemagick `convert` seems to produce decent output, for some reason.
    http = httplib2.Http()
    response = http.request("http://monty2.ccnmtl.columbia.edu:5052/", method="POST", body=output)

    name = datetime.datetime.now().strftime("%s")

    graph_dir = settings.MVSIM_GRAPH_OUTPUT_DIRECTORY
    path = os.path.join(graph_dir, "%s.png" % name)

    fp = open(path, "w")
    fp.write(response[1])
    fp.close()

    return HttpResponse(name, mimetype="text/plain")
    
@rendered_with("graphing/graph.html")
def graph(request, game_id):
    game = Game.objects.get(pk=game_id)

    if not game.viewable(request):
        return forbidden()

    turns = [game.deserialize(state) for state in game.state_set.order_by("created")]

    params = {}
    
    primary_layers = []
    
    primary_xaxis = None
    secondary_xaxis = None
    
    layer_names = {}
    kw = request.GET
    for key in kw:
        if key == "primary_xaxis":
            primary_xaxis = kw['primary_xaxis']
            continue
        if key == "secondary_xaxis":
            secondary_xaxis = kw['secondary_xaxis']
            continue
            
        if key.endswith("_label"):
            layer = key[:-1*len("_label")]
            name = kw[key]
            layer_names[layer] = name
            continue

        if key == "primary":
            for val in kw.getlist(key):
                primary_layers.append(val)
            continue

        for val in kw.getlist(key):
            params.setdefault(key, []).append(val)

    params = params or {"layer_1": []}
    primary_layers = sorted(primary_layers) or []

    all_variables = game.configuration.variables.all()
    excluded_variables = (
        'calculated_food_cost',
        'cotton_yield',
        'energy_req',
        'fertilizer_last_turn',
        'fertilizer_t1',
        'fertilizer_t2',
        'fish_coeff',
        'food_yield',
        'initial_population',
        'market',
        'maximum_effort',
        'propane_fuel',
        'season',
        'try_for_child',
        'wood_coeff',
        'wood_fuel',
        'year',
        )
    class BoundVariable(object):
        def __init__(self, name, getter=None, descriptive_name=None):
            self.name = name
            self.descriptive_name = descriptive_name or name.replace("_", " ").title()
            self.values = []
            for turn in turns:
                if getter is None:
                    self.values.append(
                        turn.variables[name])
                else:
                    self.values.append(
                        getter(turn, name))
    variables = []
    def add_divided_farming():
        # in addition to effort_farming, we also want to calculate
        # separate variables for each turn's effort farming spent
        # on each of maize and cotton
        def getter(turn, name):
            total_effort = turn.variables.effort_farming
            plots = turn.variables.crops
            if name == "effort_farming_maize":
                amount = sum(1 for i in plots if i == "Maize")
            elif name == "effort_farming_cotton":
                amount = sum(1 for i in plots if i == "Cotton")
            amount = 1.0 * amount / len(plots)
            return total_effort * amount
    
        variables.append(BoundVariable("effort_farming_maize", getter, "Effort Farming Maize (person-hours/day)"))
        variables.append(BoundVariable("effort_farming_cotton", getter, "Effort Farming Cotton (person-hours/day)"))
    def add_divided_health():
        # since health is a compound variable, we want to split it apart
        # into individual variables for each family member
        def getter(turn, name):
            health = turn.variables.health
            person_name = name[len("health_"):].title() # name will be like health_kodjo
            names = turn.variables.names
            try:
                index = names.index(person_name)
            except ValueError:
                # this person was not yet born, or was dead, at this turn
                return 0 
            return health[index]
        # we need to figure out all the people who were ever part of the family
        all_names = {}
        for turn in turns:
            names = turn.variables.names
            for name in names:
                all_names[name] = "health_" + name.lower()
        for name, var_name in all_names.items():
            variables.append(BoundVariable(
                    var_name, getter, 
                    "Health %s " % name + "(%)"))
    def add_average_health():
        # since health is a compound variable, we want to split it apart
        # into individual variables for each family member
        def getter(turn, name):
            health = turn.variables.health
            names = turn.variables.names
            if len(names) == 0:
                return 0
            return sum(health) / len(names)
        variables.append(BoundVariable(
                "health_average", getter,
                "Average Family Health (%)"))
    
    def add_divided_sickness():
        # since sick is a compound variable, we want to split it apart
        # into individual variables for each family member
        def getter(turn, name):
            sick = turn.variables.sick
            person_name = name[len("sick_"):].title() # name will be like health_kodjo
            names = turn.variables.names
            try:
                index = names.index(person_name)
            except ValueError:
                # this person was not yet born, or was dead, at this turn
                return 0
            return int(bool(sick[index].strip()))
        # we need to figure out all the people who were ever part of the family
        all_names = {}
        for turn in turns:
            names = turn.variables.names
            for name in names:
                all_names[name] = "sick_" + name.lower()
        for name, var_name in all_names.items():
            variables.append(BoundVariable(
                    var_name, getter,
                    "%s Sick" % name))
    def add_percent_sickness():
        def getter(turn, name):
            sick = turn.variables.sick
            names = turn.variables.names
            if len(names) == 0:
                return 0
            return 1.0 * sum(bool(i.strip()) for i in sick) / len(names)
        variables.append(BoundVariable(
                "sick_percent", getter,
                "Family Sick (% of family)"))
    for variable in all_variables:
        if variable.name in excluded_variables:
            continue
        if variable.name == "health":
            add_divided_health()
            add_average_health()
            continue
        if variable.name == "sick":
            add_divided_sickness()
            add_percent_sickness()
            continue
        if variable.type == "bool":
            def getter(turn, name):
                value = turn.variables[name]
                return int(value)
            variables.append(BoundVariable(
                    variable.name, getter,
                    variable.description))
            continue
        if not variable.graphable():
            continue
        variables.append(BoundVariable(
                variable.name,
                descriptive_name=variable.description))
        if variable.name == "effort_farming":
            add_divided_farming()
    
    return dict(game=game,
                params=params,
                variables=variables,
                primary_xaxis=primary_xaxis,
                secondary_xaxis=secondary_xaxis,
                primary_layers=primary_layers,
                layers=params,
                layer_names=layer_names,
                turns=turns)
    
    
