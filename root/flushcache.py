
def main():
	from google.appengine.api import memcache
	memcache.flush_all()
	print "Cache has been flushed."

if __name__ == '__main__':
	main()
