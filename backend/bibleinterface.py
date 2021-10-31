"""
bibleinterface.py

Exposes an interface onto a manager for bibles, commentaries, dictionaries and
generic books
"""
from swlib.pysw import SW
from swlib import pysw

from backend.book import Bible, Commentary
from backend.dictionary import Dictionary, DailyDevotional

from util import confparser
from util.observerlist import ObserverList
from util.debug import dprint, MESSAGE, WARNING, ERROR
from backend.filter import MarkupInserter
from backend.filterutils import NORMAL_PARSER_MODE
from backend.genbook import GenBook, Harmony
import config

class BibleInterface(object):
	def __init__(self, biblename="ESV", commentaryname="TSK",
	  		dictionaryname="ISBE", genbook="Josephus", daily_devotional_name="",
			harmonyname="CompositeGospel"):

		self.on_before_reload = ObserverList()
		self.on_after_reload = ObserverList()
		self.reloading = False

		self.mgrs = []
		self.paths = []
		
		dprint(MESSAGE, "Creating manager")

		self.make_managers()
		
		# call on after reload in case
		self.on_after_reload(self)
		

		dprint(MESSAGE, "/Creating manager")

		self.bible = Bible(self, biblename) 
		self.commentary = Commentary(self, commentaryname)
		self.dictionary = Dictionary(self, dictionaryname)
		self.genbook = GenBook(self, genbook) 
		self.daily_devotional = DailyDevotional(self, daily_devotional_name)
		self.harmony = Harmony(self, harmonyname)
		
		self.state = []
		self.options = {}
		self.init_options()

		self.book_type_map = {
			self.bible.type:		self.bible,
			self.commentary.type:	self.commentary,
			self.dictionary.type:	self.dictionary,
			self.genbook.type:		self.genbook,
		}

		self.book_category_map = {
			self.daily_devotional.category:	self.daily_devotional,
			self.harmony.category:			self.harmony,
		}

		self.parser_mode = NORMAL_PARSER_MODE
	
	def init_options(self):
		for option, values in self.get_options():
			for path, mgr, modules in self.mgrs:
				option_value = mgr.getGlobalOption(option)

				# if NULL is ever a valid value for this, 
				# this code may mean that a default 
				# option value is not set in the options.
				if option_value is not None:
					self.options[option] = option_value
		
		#if people want no extras, here it is
		self.temporary_state()
		for option, values in self.get_options():
			self.set_option(option, values[0])

		self.plainstate = self.save_state()
		self.restore_state()
   

	def set_option(self, option, value=True):
		processed_value = value
		if type(value) == bool:
			processed_value = {True:"On", False:"Off"}[value]

		for path, mgr, modules in self.mgrs:
			mgr.setGlobalOption(str(option), str(processed_value))

		self.options[option] = processed_value
	
	def temporary_state(self, options = None):
		self.state.append(dict(self.options))
		if(options):
			for key, value in options.items():
				self.set_option(key, value)
		
	
	def restore_state(self):
		if not self.state:
			return
		state = self.state.pop()

		#restore state
		for key, value in state.items():
			self.set_option(key, value)

	def save_state(self):
		return dict(self.options)
	
	def get_module(self, mod):
		return self.modules.get(mod)

	def get_module_book_wrapper(self, module_name):
		mod = self.modules_with_lowercase_name.get(module_name.lower())
		if mod is None:
			dprint(ERROR, "Mod is none", module_name)
			return None

		category = mod.getConfigEntry("Category")
		if category and (category in self.book_category_map):
			book = self.book_category_map[category]
		else:
			book = self.book_type_map.get(mod.Type())
			if book is None:
				dprint(ERROR, "book is none", module_name, mod.Type())
				return None

		book.SetModule(mod)
		return book
	
	def _get_modules(self):
		self.modules = {}
		self.modules_with_lowercase_name = {}
		self.headwords_modules = {}
		for path, mgr, modules in self.mgrs:
			headwords_modules = [(name, module) for name, module in modules if
				module.getConfigEntry("HeadwordsDesc") is not None]
			
			modules = [(name, module) for name, module in modules if
				module.getConfigEntry("HeadwordsDesc") is None]				

			self.modules.update(modules)
			self.headwords_modules.update(headwords_modules)
			self.modules_with_lowercase_name.update(
					(name.lower(), module) for  name, module in modules)

	@property
	def all_modules(self):
		mods = self.modules.copy()
		mods.update(self.headwords_modules)
		return mods
				
	def get_options(self):
		option_names = []
		options = {}

		for path, mgr, modules in self.mgrs:
			# I'm not sure if one SWMgr can include 3 options for a
			# value, and another two. (for example)
			# if so, we choose the last one
			
			for option_name in mgr.getGlobalOptionsVector():
				text = option_name.c_str()
	
				options[text] = []
				
				if text not in option_names:
					option_names.append(text)

				for option_value in mgr.getGlobalOptionValuesVector(text):
					options[text].append(option_value.c_str())
		
		# sort it by order received
		return [(option, options[option]) for option in option_names]
	
	def get_tip(self, option):
		for path, mgr, modules in reversed(self.mgrs):
			tip = mgr.getGlobalOptionTip(option)
			if tip:
				return tip
			
	def load_paths(self, filename=config.sword_paths_file):
		config_parser = confparser.config()
		try:
			f = open(filename)
			config_parser._read(f, filename)
		except EnvironmentError:
			return ["resources"]

		data_path = "resources"

		if config_parser.has_option("Install", "DataPath"):
			data_path = config_parser.get("Install", "DataPath")[0]

		if config_parser.has_option("Install", "AugmentPath"):
			paths = config_parser.get("Install", "AugmentPath")[::-1]
			if data_path and data_path not in paths:
				paths.append(data_path)
		else:
			paths = [data_path]

		if "resources" not in paths:
			paths.append("resources")

		return paths
	
	def write_paths(self, paths, filename=config.sword_paths_file):
		paths = paths[::-1]
		config_parser = confparser.config()
		config_parser.read(filename)
		if not config_parser.has_section("Install"):
			config_parser.add_section("Install")
		
		config_parser.set("Install", "DataPath", paths[0])
		config_parser.set("Install", "AugmentPath", [])

		# We set the locale path to a dummy directory to give us greater
		# control of the locale setup process.
		config_parser.set("Install", "LocalePath", "locales\\dummy")
		
		augment_paths = config_parser.get("Install", "AugmentPath")
		del augment_paths[0]
		augment_paths.extend(paths[1:])

		config_parser.write(open(filename, "w"))
	
	def set_new_paths(self, paths=None, path_changed=None):
		self.reloading = True
		bible		= self.bible.version
		dictionary  = self.dictionary.version
		commentary  = self.commentary.version
		genbook     = self.genbook.version
		harmony     = self.harmony.version
		daily       = self.daily_devotional.version
		
		items = [
			(self.genbook, genbook),
			(self.harmony, harmony),
			(self.dictionary, dictionary), 
			(self.daily_devotional, daily),
			(self.commentary, commentary), 
			
			# do bible last, so that the others will have been notified of
			# their version changes before it notifies them it has changed
			(self.bible, bible), 
			
		]

		if path_changed is None:
			self.mgrs = []
			if paths:
				self.write_paths(paths)

		self.on_before_reload(self)
		self.make_managers(path_changed)

		for item, module in items:
			# put the items on hold so that they don't fire until all modules
			# are changed
			item.observers.hold()
			
		for item, module in items:
			if item.ModuleExists(module):
				item.SetModule(module)
				continue

			mods = item.GetModuleList()
			if mods:
				item.SetModule(mods[0])
			else:
				item.SetModule(None)
		
		# turn our items on again
		for option, value in self.options.iteritems():
			self.set_option(option, value)

		self.init_options()

			
		
		for item, module in items:
			item.observers.finish_hold()
		
		self.reloading = False
		
		# do the on_after_reload *after* the hold finishing so that the
		# genbook can work out its treekey stuff before it is refreshed
	    #TODO: this needs to happen before the modules get reloaded
		# so that the strong's numbers are set up
		
		self.on_after_reload(self)
	
	reload = set_new_paths		
			
	def make_managers(self, path_changed=None):
		# turn off logging
		system_log = SW.Log.getSystemLog()
		log_level = system_log.getLogLevel()
		system_log.setLogLevel(0)
		try:
			if path_changed is None:
				paths = self.load_paths()[::-1]
				for item in paths:
					mgr = self.make_manager(item)
					modules = [(name.c_str(), mod) for name, mod 
								in mgr.getModules().iteritems()]
					self.mgrs.append([item, mgr, modules])
			
				self.paths = paths
				
			else:
				for item in self.mgrs:
					if item[0] != path_changed:
						continue

					item[1] = mgr = self.make_manager(item[0])
					item[2] = [(name.c_str(), mod) for name, mod 
								in mgr.getModules().iteritems()]

			self._get_modules()

		finally:
			# reset it to what it was
			system_log.setLogLevel(log_level)	

	def make_manager(self, path):
		markup_inserter = MarkupInserter(self)
		
		markup = SW.MyMarkup(markup_inserter, 
			SW.FMT_HTMLHREF)#, SW.ENC_HTML)
		
		#markup = SW.MarkupFilterMgr(SW.FMT_HTMLHREF, SW.ENC_HTML)
		markup.thisown = False

		# don't augment home path
		mgr = SW.Mgr(path, True, markup, False, False)
	
		return mgr

biblemgr = BibleInterface("ESV", "TSK", "ISBE") 

biblemgr.genbook.templatelist.append(config.genbook_template)
biblemgr.harmony.templatelist.append(config.genbook_template)
biblemgr.dictionary.templatelist.append(config.dictionary_template)
biblemgr.daily_devotional.templatelist.append(config.dictionary_template)
biblemgr.commentary.templatelist.append(config.commentary_template)
biblemgr.bible.templatelist.append(config.bible_template)

# TODO: TESTING
for option, values in biblemgr.get_options():
	if "On" in values:
		biblemgr.set_option(option, "On")
