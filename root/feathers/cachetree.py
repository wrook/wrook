"""
cachetree module from the feathers toolkit
cachetree is a caching utility which provide basic cache invalidation through the use of composite keys.
"""

import datetime
import logging
from google.appengine.ext import db
from google.appengine.api import memcache

class Cachable(db.Model):
	Timestamp =  db.DateTimeProperty(auto_now_add=True)
		
	def touch(self):
		self.Timestamp = datetime.datetime.now()
		self.update_cache()
		self.invalidate_cache_collections()

	def update_cache(self):
		logging.debug("self = %s " % self)
		logging.debug("update_cache(%s)" % self.get_cache_key())
		memcache.set(self.get_cache_key(), self)
		self.update_cache_meta()

	def update_cache_meta(self):
		#Refreshes the reference cache metadata
		meta = {"Timestamp": self.Timestamp}
		memcache.set("%s-meta" % self.get_cache_key(), meta)
	
	def get_cache_key(self):
		# Returns the simplest possible cache key for this asset
		# Should be overwritten if something more specific is needed
		return "%s" % self.key()
	
	def invalidate_cache_collections():
		# This method should be overwritten with the logic necessary
		# to invalidate the cache meta for collections containing this entity
		pass

def get_fresh_cache(key, dependencyKeys):
	isFresh = True
	itemMeta = memcache.get("%s-meta" % key)
	timestamp = None
	if itemMeta:
		for depKey in dependencyKeys:
			logging.debug("fetching meta: %s-meta " % depKey)
			meta = memcache.get("%s-meta" % depKey)
			if not meta: continue
			if not meta.get("Timestamp"): continue
			logging.debug("comparing dep:%s > itm:%s " % (meta.get("Timestamp"), itemMeta.get("Timestamp")))
			if (meta.get("Timestamp") > itemMeta.get("Timestamp")):
				isFresh = False
				break
		if isFresh:
			logging.debug("found: get_fresh_cache(%s, %s)" % (key, dependencyKeys))
			return memcache.get(key)
		logging.debug("no meta (get_fresh_cache)")
	logging.debug("not found: get_fresh_cache(%s, %s)" % (key, dependencyKeys))
	return None

def old_get(key):
	logging.debug("cachetree.get(%s)" % key)
	#get timestamp from cache metadata
	if key:
		parentKey = key.split("::",1)[0]
		meta = memcache.get(key)
		if meta:
			parentMeta = memcache.get(parentKey)
			if not parentMeta:
				logging.debug("Fresh cached data found: %s", key)
				return meta.get("data")
			logging.debug("Comparing timestamps: %s > %s" %
				(meta.get("timestamp"), parentMeta.get("timestamp")))
			if meta.get("timestamp") > parentMeta.get("timestamp"):
				#if still valid get data from cache
				logging.debug("Fresh cached data found: %s", key)
				return meta.get("data")
			else:
				logging.debug("Cached data was stale: %s", key)
				return None
		else:
			logging.debug("No cache found: %s", key)
			return None
	else:
		logging.debug("No keys provided")
		return None


def touch(key):
	timestamp = datetime.datetime.now()
	meta = {"Timestamp": timestamp}
	memcache.set("%s-meta" % key, meta)

def get(key):
	logging.debug("Getting cache data for : %s" % key )
	return memcache.get(key)

def add(key, data):
	logging.debug("Caching data to : %s" % key )
	memcache.add(key, data)
	memcache.add("%s-meta" % key, {"Timestamp":datetime.datetime.now()})
	logging.debug("Done caching to : %s" % key )

def set(key, data):
	logging.debug("Caching data to : %s" % key )
	memcache.set(key, data)
	memcache.set("%s-meta" % key, {"Timestamp":datetime.datetime.now()})
	logging.debug("Done caching to : %s" % key )


