#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi, re
import pygraphviz as pgv
from threading import Thread
from Queue import Queue
winner, loser = 1, 0

class Source(object):
    def winner(self):
        return None   
    def loser(self):
        return None
    slot_winner = None
    slot_loser = None

class Team(Source):
    def __init__(self, id, players):
        self.id = id
        self.players = players.replace('\n','')
    def winner(self):
        return [ self ]           
    def __repr__(self):
        return self.players
    def matches_info(self): 
        matches=[]
        slot = self.slot_winner
        match = slot.match        
        while slot:
            if slot == match.slot1:
                this, other = match.slot1, match.slot2
            else:
                this, other = match.slot2, match.slot1           
            if this.score > other.score:
                slot = match.slot_winner
                points = match.points
            else:
                slot = match.slot_loser
                points = 0
            matches.append((match, points, not this.score == other.score))
            if this.score == other.score:
                break
            if slot:
                match = slot.match                            
        return matches    
    def played(self):
        return [ x[2] for x in self.matches_info() ].count(True)
    def points(self):
        return sum( [ x[1] for x in self.matches_info() ] )
    def matches(self):
        return( [ x[0] for x in self.matches_info() ] )

class Slot(object):    
    def __init__(self, source, type=winner):
        self.type = type
        self.source = source
        if self.type == winner:
            source.slot_winner = self
        else:
            source.slot_loser = self        
    def teams(self):
        if self.type == winner:
            return self.source.winner()
        else:
            return self.source.loser()      
    def team(self):
        teams = self.teams()
        if len(teams) == 1:
            return teams[0]
        else:
            return Team(0,"")
    def id(self):
        return str(self.match.id)+"_"+str(self.pos)
    def filename(self):
        return "scores/"+self.id()
    def load(self):
        try:
            f = open(self.filename())
            self.score=int(f.readline())
            f.close()
        except:
            pass
    def save(self):
        f = open(self.filename(), "w")
        f.write(str(self.score))
        print self.filename()+": "+str(self.score)
        f.close()
    score = 0    

class Match(Source):
    def __init__(self, id, slot1, slot2, round=0, points=1):
        self.slot1 = slot1
        self.slot1.pos=1
        self.slot1.match = self
        self.slot2 = slot2
        self.slot2.pos=2
        self.slot2.match = self
        self.points = points
        self.round = round
        self.id = id
        self.slot1.load()
        self.slot2.load()
    def winner(self):
        if self.slot1.score > self.slot2.score:
            return self.slot1.teams()
        elif self.slot2.score > self.slot1.score:
            return self.slot2.teams()
        else:
            return self.slot1.teams() + self.slot2.teams()    
    def loser(self):
        if self.slot1.score < self.slot2.score:
            return self.slot1.teams()
        elif self.slot2.score < self.slot1.score:
            return self.slot2.teams()
        else:
            return self.slot1.teams() + self.slot2.teams()
    def __repr__(self):
        return repr(self.slot1.team()) + " (" + str(self.slot1.score)+ ") vs. " + repr(self.slot2.team()) + " (" + str(self.slot2.score) +")"

class TournamentHandler(BaseHTTPRequestHandler):
    def ok(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
    def header(self, title, bgcolor='bisque'):
        title = cgi.escape(title)
        header = "<html><head><style>th {font-size: 80%; color: gray} h1 { font-size: 120%; color: gray} "
        header += "table { border-collapse: collapse } a { color: black} .m { background: "+bgcolor+" }</style>"
        header += "<title>"+title+"</title></head><body style='font-family:helvetica'><a href='teams'><div style='width:25em;margin:0 auto 0;'>Teams</a> - Rounds "
        for i in sorted(round_map.keys()):            
            header += "<span style='background:"+round_colors[i]+"'>&nbsp;<a href='"+str(i)+".round'>"+str(i)+"</a>&nbsp;</span>"
        header += " - <a href='graph'>Graph</a><h1>"+title+"</h1>"
        return header
    def footer(self):
        return "</div></body></html>"
    def team_link(self, team):
        return "<a href='"+str(team.id)+".team'>"+cgi.escape(team.players)+"</a>"
    def combo_box(self, slot):
        combo="<form style='height: 0.5em' name='f"+slot.id()+"' method='POST' action='"
        combo+=slot.id()+".slot'><select name='score' onchange='f"+slot.id()+".submit();'>"
        for i in range(0,14):
            if slot.score == i:
                s=" selected"
            else:
                s=""
            combo+="<option value='"+str(i)+"' "+s+">"+str(i)+"</option>"
        combo+="</select></form>"
        return combo
    def display_slot(self, slot):        
        if len(slot.teams())==1:
            return self.team_link(slot.team())
        else:
            r="<a href='#' onclick=\"s=getElementById('d"+slot.id()+"').style; s.display = ( s.display=='none' ? 'block' : 'none');\">...</a><span id='d"
            r+=slot.id()+"' style='display:none'>"
            r+=" | ".join([ self.team_link(team) for team in slot.teams()])+"</span>"
            return r
    def display_match(self, match, info, round=False):
        if round:
            info_block = "<a href='"+str(info)+".round'>"+str(info)+"</a>"
        else:
            info_block = str(info)
        self.wfile.write("<tr><td colspan='3'></td></tr>")    
        self.wfile.write("<tr><td align='center' rowspan='2' class='m'>"+info_block+"</td><td style='width: 15em' class='m'>")
        self.wfile.write(self.display_slot(match.slot1)+"</td><td class='m'>"+self.combo_box(match.slot1)+"</td></tr>")  
        self.wfile.write("<tr><td class='m'>"+self.display_slot(match.slot2)+"</td><td class='m'>"+self.combo_box(match.slot2)+"</td></tr>")        
    def do_GET(self):        
        if self.path.endswith("teams"):            
            self.ok()
            self.wfile.write(self.header("Teams")+"<table><tr><th style='width: 15em'>Players</th><th>Played</th><th>Points</th></tr>")
            for team in reversed(sorted(teams, key=lambda team: team.points())):
                self.wfile.write("<tr class='m'><td>"+self.team_link(team)+"</td><td>"+str(team.played())+"</td><td>"+str(team.points())+"</td></tr>")
            self.wfile.write("</table>"+self.footer())
        elif self.path.endswith(".team"):
            id = re.match(r'^.*[^0-9]+([0-9]+)\.team$', self.path).group(1)
            team = team_map[int(id)]
            self.ok()
            self.wfile.write(self.header(team.players)+"<p>Played "+str(team.played()))
            self.wfile.write(", got "+str(team.points())+" points.<p><table><tr><th>Round</th><th>Match</th><th>Result</th></tr>")
            for match in team.matches():
                self.display_match(match, match.round, True)
            self.wfile.write("</table>"+self.footer())
        elif self.path.endswith(".round"):
            id = re.match(r'^.*[^0-9]+([0-9]+)\.round$', self.path).group(1)
            self.ok()
            self.wfile.write(self.header("Round "+id,round_colors[int(id)])+"<table><tr><th>Court</th><th>Match</th><th>Result</th></tr>")
            i=1
            for match in round_map[int(id)]:
                self.display_match(match, i)
                i+=1
            self.wfile.write("</table>"+self.footer())         
        elif self.path.endswith("graph"):   
            self.ok()
            self.wfile.write(self.header("Graph")+"<img src='graph.png'>"+self.footer())      
        elif self.path.endswith("graph.png"):
            self.send_response(200)
            self.send_header('Content-type', 'image/png')
            self.end_headers()
            f=open("graph.png", "rb")
            self.wfile.write(f.read())
            f.close()
        else:
            self.send_response(302)
            self.send_header('Location', 'teams')
            self.end_headers()
    def do_POST(self):
        if self.path.endswith(".slot"):
            m = re.match(r'^.*[^0-9]+([0-9]+)_([0-9]+)\.slot$', self.path)
            match = match_map[int(m.group(1))]
            slot_id = int(m.group(2))
            form = cgi.parse_qs(self.rfile.read(int(self.headers.getheader('Content-Length'))))            
            score = int(form['score'][0])
            if slot_id == 1:
                slot = match.slot1
            else:
                slot = match.slot2
            slot.score = score
            slot.save()
        update_graph()
        self.send_response(302)
        self.send_header('Location', self.headers["Referer"] if self.headers.has_key("Referer") else "/")
        self.end_headers()
def graph():
    G=pgv.AGraph(directed=True,nodesep='0.5',splines='false')
    for match in matches:
        G.add_node("m"+str(match.id), label='{ <s1> '+match.slot1.team().players +' | <s2> '+ match.slot2.team().players+' }', 
            shape='record', style='filled', color=round_colors[match.round], fontsize='8', fontname='Helvetica')
    for match in matches:     
        if type(match.slot1.source)==Match:
            G.add_edge('m'+str(match.slot1.source.id), 'm'+str(match.id), style='bold', color='green3' if match.slot1.type==winner else 'red3')     
        if type(match.slot2.source)==Match:
            G.add_edge('m'+str(match.slot2.source.id), 'm'+str(match.id), style='bold', color='green3' if match.slot2.type==winner else 'red3')                   
    import sys
    if len(sys.argv) == 1:
        alg='dot'
    else:
        alg=sys.argv[1]
    G.draw('graph.png', prog=alg)

round_colors = { 1: '#F5F5DC', 2: '#7FFFD4', 3: '#F0E68C', 4: '#E9967A' }
teams = [ ]
i=1
for line in open('teams.txt','r').readlines():
    teams.append(Team(i,line))
    i+=1
team_map = {}
for team in teams:
    team_map[team.id] = team
matches = []
m=1
for i in range(len(teams)/2):
    matches.append(Match(m, Slot(teams[i*2]), Slot(teams[i*2+1]), 1, 1))
    m+=1
for i in range(0,2):
    matches.append(Match(m, Slot(matches[i*2]), Slot(matches[i*2+1]), 2, 2))
    m+=1
for i in range(0,2):
    matches.append(Match(m, Slot(matches[i*2], loser), Slot(matches[i*2+1], loser), 2, 2))
    m+=1
for i in range(2,4):
    matches.append(Match(m, Slot(matches[i*2]), Slot(matches[i*2+1]), 3, 4))
    m+=1
for i in range(2,4):
    matches.append(Match(m, Slot(matches[i*2], loser), Slot(matches[i*2+1], loser), 3, 4))
    m+=1
for i in range(4,6):
    matches.append(Match(m, Slot(matches[i*2]), Slot(matches[i*2+1]), 4, 8))
    m+=1
for i in range(4,6):
    matches.append(Match(m, Slot(matches[i*2], loser), Slot(matches[i*2+1], loser), 4, 8))
    m+=1
match_map = {}
round_map = {}
for match in matches:
    match_map[match.id] = match
    if not match.round in round_map.keys():
        round_map[match.round] = []
    round_map[match.round].append(match)
events = Queue()
def update_graph():
    events.put(object())
looping=True
def loop():
    while events.get():
        if not looping:
                break
        graph()
Thread(target=loop).start()
update_graph()
try:
    server = HTTPServer(('', 8888), TournamentHandler)
    print 'started httpserver...'
    server.serve_forever()
except KeyboardInterrupt:
    print '^C received, shutting down server'
    server.socket.close()
    looping=False
    update_graph()