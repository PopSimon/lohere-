import IPAddress from ipaddr.py
import BanTable
import SessionRepo

#
# Concept arra, nagyjából mit kéne tudnia a session-öknek és hogyan állítsuk elő őket
# Sok a hiányzó/esetleg hibás rész még mivel egyrész kezdő vagyok pájtonban, másrészt nagyon kezdő vagyok flaskban
#

class Fingerprint:
	'''
		A request információi alapján az userről összeállított ujjlenyomat.
	'''
	def __init__(self, address, ua_string):
		# TODO
		self.address = address
		self.ua_string = ua_string
		
def fingerprint_from_req(req):
	# TODO
	return Fingerprint(IPAddress(req.ip), req.ua_string)

def fingerprint_from_db(db_rec):
	# TODO
	return Fingerprint(IPAddress(db_rec.ip), db_rec.ua_string)

	
class SID:
    '''
        Biztonságos session id, autentikált sessionökhöz.
    '''
    def __init__(self, id):
        if type(id) is not int:
            raise TypeError("SID should be int")
        this.value = id
    def __eq__(self, sid):
        return self.value == sid.value if type(sid) is SID else None
        
def generate_sid():
    '''
        Biztonságos véletlenszám-generátorral új SID-et generál
        Használata: pl. amikor egy user bejelentkezik és új AuthSession-t kap
    '''
    raise NotImplemented # TODO
	
class FakeSID(SID):
    '''
        Placeholder session id.
        Az anonymous felhasználók esetén használatos csak, bejelentkezéshez más fajta sid-t használunk.
        Csupán valamiféle általános jellegű egyszerű azonosításra szolgál, biztonsági szempontból semmi funkciója nincs.
        Pl.: a viccesnevek (többek közt) ez alapján generálódnak
        A felhasználó ip-címének és user agent stringjének valami hashe, ezt a kettőt minden query esetén ismerjük és viszonylag jó azonosító
    '''
    def __eq__(self, sid):
        return self.value == sid.value if type(sid) is FakeSID else None

def generate_fsid(fingerprint):
    '''
        A felhasználó fingerprintjéből FakeSID-t generál.
        A használt hash metódus abból a szempontból lehet kritikus, ne lehessen adott
        ip-hez és threadhez (könnyen) kifundálni olyan ua stringet, amivel előre le lehessen foglalni egy fsid-t
        Használata: minden bejövő anonymous session esetén meghívódik
    '''
    raise NotImplemented # TODO

class UserData:
	def __init__(self, skin, alias, alias_control, email, sage, spoiler, noko):
        # Skin
        self.skin = skin or None # None esetén az adott view (board) defaultját használjuk majd
        # Form
        self.alias = alias or ""
        self.alias_control = alias_control or None # None esetén az adott view (board) defaultját használjuk majd
        self.email = email or ""
        self.sage = sage or False
        self.spoiler = spoiler or False
        self.noko = noko or False
	
class SessionData(UserData):
    '''
        Az adott sessionhöz köthető, a megjelenítéshez kapcsolódó különböző információk
		A válaszban sütiben visszaküldjük.
    '''
	def __init__(self, form, cookie, user):
		if user:
			skin = user.data["skin"]
			alias = user.data["alias"]
			alias_control = user.data["alias_control"]
			email = user.data["email"]
			sage = user.data["sage"]
			spoiler = user.data["spoiler"]
			noko = user.data["noko"]
		if cookie: # a sütiben érkező mezőkből feltöltés
			skin = cookie["skin"] or skin
			alias = cookie["alias"] or alias
			alias_control = cookie["alias_control"] or alias_control
			email = cookie["email"] or email
			sage = cookie["sage"] or sage
			spoiler = cookie["spoiler"] or spoiler
			noko = cookie["noko"] or noko
		if form: # felülírjuk a form-ban beérkező adatokkal az eddigit, ha post-ol a júzer éppen
			skin = form["skin"] or skin
			alias = form["alias"] or alias
			alias_control = form["alias_control"] or alias_control
			email = form["email"] or email
			sage = form["sage"] or sage
			spoiler = form["spoiler"] or spoiler
			noko = form["noko"] or noko
		super(UserData, self).__init__(skin, alias, alias_control, email, sage, spoiler, noko)

	
class Session:
    '''
        Session alaposztály
        
        fingerprint: a request alapján előállított ujjlenyomat
        sid: a session azonosítója
        user: a sessionhöz tartozó felhasználó, csak ha autentikált a session
        bans: a felhasználóra vonatkozó szabályok, banok listája - akár a beérkező sütiből (session ban), akár a bantáblából (ip alapján), akár a user rekord alapján
        data: a sessionhöz tartozó vegyes infók megjelenítéshez, pl. a használt css stílus, a form mező "beragadó" beállításai (alias, spoiler, sage, noko) - form, süti, user rekord alapján
    '''
    def __init__(self, fingerprint, sid, user, bans, data):
        self.fingerprint = fingerprint
        self.sid = sid
        self.user = user
		self.bans = bans
        self.data = data

class AnonymousSession(Session):
    '''
        
    '''
    def __init__(fingerprint, bans, data):
        super(AnonymousSession, self).__init__(fingerprint, generate_sid(address), None, bans, data)

class NoCookieSession(AnonymousSession):
    '''
        Az user süti nélkül jön, vagy mert még nem járt az oldalon/lejárt a régi sütije, vagy mert le vannak nála tiltva a sütik
        Az ilyen userek nem loginolhatnak, mivel a loginhoz süti kell - a problémák elkerülése végett login/reg oldalon esetleg sütiteszt
    '''
    pass
    # TODO: ha a kéréssel együtt nem érkezett süti, a felhasználónál tiltva van valószínűleg
    
class ProxySession(AnonymousSession):
    '''
        Az user valamiféle proxy-hálózat mögül (tor, i2p) érkezik és mi tudomást szereztünk róla (proxytábla).
        Az ilyen userek nem regisztrálhatnak/loginolhatnak a biztonsági problémák elkerülése (és a spambotok) végett.
    '''
    pass
    # TODO: ha a user tor-os ip-ről ír, ilyet nyitunk automatikusan

class AuthSession(Session):
    '''
        Autentikált user sessionje.
    '''
    def __init__(fingerprint, sid, user, bans, data):
        super(AnonymousSession, self).__init__(fingerprint, sid, user, bans, data)
    
    
def generate_session(req):
    fprint = fingerprint_from_req(req)
    cookies = req.cookies
	
	# ip-banok ellenőrzése
	bans = BanTable.get(address)
    
	# incoming SID a sütikből
	if "session" in cookies:
		sid = cookies["session"].sid
		SessionRepo.check(sid, fprint) # incoming SID ellenőrzése - a session táblából, esetleg ip, ua_string ellenőrzése?
    
	# data
	data = SessionData(form, data_cookie, user)
		
	if address in ProxyTable: # ProxyTable-ben __contains__ felülírva, hogy ip-rangeket is megtalálja
		return ProxySession(address, bans, data)
    else if sid:
        return AuthSession(address, sid, user, bans, data)
    # ellenben generált SID
    else if cookie:
		return AnonymousSession(address, bans, data)
	else:
		return NoCookieSession(address, bans, data)
		
