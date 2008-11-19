#!/usr/bin/python2.4

"""MobWrite - Real-time Synchronization and Collaboration Service

Copyright 2008 Neil Fraser
http://code.google.com/p/google-mobwrite/

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""This file is the server, running under Google App Engine.

Accepting synchronization sessions from clients.
"""

__author__ = "fraser@google.com (Neil Fraser)"

import logging
import cgi
import urllib
import datetime
import re
import diff_match_patch as dmp_module
from google.appengine.ext import db
from google.appengine import runtime

# Demo usage should limit the maximum size of any text.
# Set to 0 to disable limit.
MAXCHARS = 50000

# Global Diff/Match/Patch object.
dmp = dmp_module.diff_match_patch()

def main():
  # Choose from: CRITICAL, ERROR, WARNING, INFO, DEBUG
  logging.getLogger().setLevel(logging.DEBUG)

  form = cgi.FieldStorage()
  if form.has_key('q'):
    # Client sending a sync.  Requesting text return.
    print 'Content-Type: text/plain'
    print ''
    print parseRequest(form['q'].value)
  elif form.has_key('p'):
    # Client sending a sync.  Requesting JS return.
    print 'Content-Type: text/javascript'
    print ''
    value = parseRequest(form['p'].value)
    value = value.replace("\\", "\\\\").replace("\"", "\\\"")
    value = value.replace("\n", "\\n").replace("\r", "\\r")
    print "mobwrite.syncRun2_(\"%s\");" % value
  elif form.has_key('clean'):
    # External cron job to clean the database.
    print 'Content-Type: text/plain'
    print ''
    cleanup()
  else:
    # Unknown request.
    print 'Content-Type: text/plain'
    print ''

  logging.debug("Disconnecting.")


class TextObj(db.Model):
  # An object which stores a text.

  # Object properties:
  # .text - The text itself.
  # .lasttime - The last time that this text was modified.

  text = db.TextProperty()
  lasttime = db.DateTimeProperty(auto_now=True)

  def setText(self, text):
    # Scrub the text before setting it.
    # Keep the text within the length limit.
    if MAXCHARS != 0 and len(text) > MAXCHARS:
       text = text[-MAXCHARS:]
       logging.warning("Truncated text to %d characters." % MAXCHARS)
    # Normalize linebreaks to CRLF.
    text = re.sub(r"(\r\n|\r|\n)", "\r\n", text)
    if (self.text != text):
      self.text = text
      self.put()
      logging.debug("Saved %db TextObj: '%s'" %
                    (len(text), self.key().id_or_name()))


def fetchText(filename):
  # DataStore doesn't like names starting with numbers.
  filename = "_" + filename
  key = db.Key.from_path(TextObj.kind(), filename)
  text = db.get(key)
  # Should be zero or one result.
  if text != None:
    logging.debug("Loaded %db TextObj: '%s'" % (len(text.text), filename))
    return text
  logging.debug("Created new TextObj: '%s'" % filename)
  return TextObj(key_name=filename)


class ViewObj(db.Model):
  # An object which contains one user's view of one text.

  # Object properties:
  # .username - The name for the user, e.g 'fraser'
  # .filename - The name for the file, e.g 'proposal'
  # .mytext - The last version of the text sent to client.
  # .lasttime - The last time (in seconds since 1970) that a web connection
  #     serviced this object.
  # .textobj - The shared text object being worked on.
  # .changed - Does this object need to be saved.

  username = db.StringProperty(required=True)
  filename = db.StringProperty(required=True)
  mytext = db.TextProperty()
  lasttime = db.DateTimeProperty(auto_now=True)
  changed = False
  textobj = None


def fetchUserViews(username):
  query = db.GqlQuery("SELECT * FROM ViewObj WHERE username = :1", username)
  # Convert list to a hash, and also load the associated text objects.
  views = {}
  for view in query:
    logging.debug("Loaded %db ViewObj: '%s %s'" %
        (len(view.mytext), view.username, view.filename))
    view.textobj = fetchText(view.filename)
    views[view.filename] = view
  if len(views) == 0:
    logging.debug("Unable to find a ViewObj for: '%s'" % username)
  return views


class BufferObj(db.Model):
  # An object which assembles large commands from fragments.

  # Object properties:
  # .name - The name (and size) of the buffer, e.g. '_alpha_12'
  # .index - Which slot in the buffer this data belongs to.
  # .data - The contents of the buffer.
  # .lasttime - The last time that this buffer was modified.

  name = db.StringProperty(required=True)
  index = db.IntegerProperty(required=True)
  data = db.TextProperty(required=True)
  lasttime = db.DateTimeProperty(auto_now=True)


def setToBuffer(name, size, index, data):
  # DataStore doesn't like names starting with numbers.
  name = "_%s_%d" % (name, size)
  id = "%s_%d" % (name, index)
  key = db.Key.from_path(BufferObj.kind(), id)
  buffer = db.get(key)
  # Should be zero or one result.
  if buffer == None:
    buffer = BufferObj(key_name=id, name=name, index=index, data=data)
    logging.debug("Created new BufferObj: '%s'" % id)
  else:
    logging.warning("Reloaded existing BufferObj: '%s'" % id)
    buffer.data = data
  buffer.put()

def getFromBuffer(name, size):
  # DataStore doesn't like names starting with numbers.
  name = "_%s_%d" % (name, size)
  query = db.GqlQuery("SELECT * FROM BufferObj WHERE name = :1 ORDER BY index", name)
  if query.count() != size:
    # Buffer not yet fully defined.
    return None
  # Assemble the buffer's contents and delete it.
  data = []
  for buffer in query:
    # Cast each part as a string (Unicode causes problems).
    data.append(str(buffer.data))
    buffer.delete()
  text = ''.join(data)
  return urllib.unquote(text)


def cleanup():
  logging.info("Cleaning database")
  try:
    # Delete any view which hasn't been written to in half an hour.
    limit = datetime.datetime.now() - datetime.timedelta(0, 0, 0, 0, 30, 0)
    query = db.GqlQuery("SELECT * FROM ViewObj WHERE lasttime < :1", limit)
    for datum in query:
      print "Deleting '%s %s' ViewObj" % (datum.username, datum.filename)
      datum.delete()

    # Delete any text which hasn't been written to in an hour.
    limit = datetime.datetime.now() - datetime.timedelta(0, 0, 0, 0, 0, 1)
    query = db.GqlQuery("SELECT * FROM TextObj WHERE lasttime < :1", limit)
    for datum in query:
      print "Deleting '%s' TextObj" % datum.key().id_or_name()
      datum.delete()

    # Delete any buffer which hasn't been written to in a quarter of an hour.
    limit = datetime.datetime.now() - datetime.timedelta(0, 0, 0, 0, 15, 0)
    query = db.GqlQuery("SELECT * FROM BufferObj WHERE lasttime < :1", limit)
    for datum in query:
      print "Deleting '%s' BufferObj" % datum.key().id_or_name()
      datum.delete()

    print "Database clean."
    logging.info("Database clean")
  except runtime.DeadlineExceededError:
    print "Cleanup only partially complete.  Deadline exceeded."
    logging.warning("Database only partially cleaned")


def parseRequest(data):
  # Passing a Unicode string is an easy way to cause numerous subtle bugs.
  if type(data) != str:
    logging.critical("parseRequest data type is %s" % type(data))
    return ""

  username = None
  filename = None
  lastUsername = None
  lastFilename = None
  echoUsername = False
  echoFilename = False
  viewobj = None
  textobj = None
  deltaOk = False
  userViews = ()
  userViewsName = None
  output = []

  for line in data.splitlines(True):
    if not (line.endswith("\n") or line.endswith("\r")):
      # Truncated line.  Abort.
      logging.warning("Truncated line: '%s'" % line)
      break
    line = line.rstrip("\r\n")
    if not line:
      # Terminate on blank line.
      break
    if line.find(":") != 1:
      # Invalid line.
      logging.warning("Invalid line: '%s'" % line)
      continue
    (name, value) = (line[:1], line[2:])

    if name == "u" or name == "U":
      if name == "U":
        # Client requests explicit usernames in response.
        echoUsername = True
      username = value
      if userViewsName != username:
        userViews = fetchUserViews(username)
        userViewsName = username
    elif name == "f" or name == "F":
      if name == "F":
        # Client requests explicit filenames in response.
        echoFilename = True
      filename = value
    elif name == "b" or name == "B":
      try:
        (name, size, index, data) = value.split(" ", 3)
        size = int(size)
        index = int(index)
      except ValueError:
        logging.warning("Invalid buffer format: %s" % value)
        continue
      # Store this buffer fragment.
      setToBuffer(name, size, index, data)
      # Check to see if the buffer is complete.  If so, execute it.
      data = getFromBuffer(name, size)
      if data:
        logging.info("Executing buffer: %s_%d" % (name, size))
        output.append(parseRequest(data))
    elif name == "r" or name == "R" or name == "d" or name == "D":
      # Edit a file.
      if not username or not filename:
        # Both a username and a filename must be specified.
        continue
      if userViews.has_key(filename):
        viewobj = userViews[filename]
      else:
        viewobj = ViewObj(username=username, filename=filename)
        logging.debug("Created new ViewObj: '%s %s'" % (username, filename))
        viewobj.mytext = u""
        viewobj.textobj = fetchText(filename)
        userViews[filename] = viewobj

      textobj = viewobj.textobj

      if name == "r" or name == "R":
        # It's a raw text dump.
        value = urllib.unquote(value).decode("utf-8")
        logging.info("Got %db raw text: '%s %s'" %
                     (len(value), viewobj.username, viewobj.filename))
        deltaOk = True
        # First, update the client's shadow.
        if viewobj.mytext != value:
          viewobj.changed = True
          viewobj.mytext = value
        if name == "R":
          # Clobber the server's text.
          if textobj.text != value:
            textobj.setText(value)
            logging.debug("Overwrote content: '%s %s'" %
                          (viewobj.username, viewobj.filename))

      elif name == "d" or name == "D":
        # It's a delta.
        # Expand the delta into a diff using the client shadow.
        logging.info("Got '%s' delta: '%s %s'" %
                     (value, viewobj.username, viewobj.filename))
        try:
          diffs = dmp.diff_fromDelta(viewobj.mytext, value)
        except ValueError:
          diffs = None
          deltaOk = False
          logging.warning("Delta failure, expected %d length: '%s %s'" %
                          (len(viewobj.mytext), viewobj.username, viewobj.filename))
        if diffs != None:
          deltaOk = True
          # First, update the client's shadow.
          patches = dmp.patch_make(viewobj.mytext, '', diffs)
          newtext = dmp.diff_text2(diffs)
          if viewobj.mytext != newtext:
            viewobj.mytext = newtext
            viewobj.changed = True
          # Second, deal with the server's text.
          if textobj.text == None:
            # A view is sending a valid delta on a file we've never heard of.
            textobj.setText("")
          if name == "D":
            # Clobber the server's text if a change was received.
            if len(diffs) > 1 or diffs[0][0] != dmp.DIFF_EQUAL:
              mastertext = viewobj.mytext
              logging.debug("Overwrote content: '%s %s'" %
                            (viewobj.username, viewobj.filename))
            else:
              mastertext = textobj.text
          else:
            (mastertext, results) = dmp.patch_apply(patches, textobj.text)
            logging.debug("Patched (%s): '%s %s'" %
                          (",".join(["%s" % (x) for x in results]), viewobj.username, viewobj.filename))
          if textobj.text != mastertext:
            textobj.setText(mastertext)

      # Process the output.
      if (echoUsername and lastUsername != username):
        output.append("u:" + username + "\n")
      lastUsername = username
      if (echoFilename and lastFilename != filename):
        output.append("f:" + filename + "\n")
      lastFilename = filename

      # Accept this view's version of the text if we've never heard of this
      # text before.
      if textobj.text == None:
        if deltaOk:
          textobj.setText(viewobj.mytext)
        else:
          textobj.setText("")

      mastertext = textobj.text
      if deltaOk:
        # Create the diff between the view's text and the master text.
        diffs = dmp.diff_main(viewobj.mytext, mastertext)
        dmp.diff_cleanupEfficiency(diffs)
        text = dmp.diff_toDelta(diffs)
        if name == "D" or name == "R":
          # Client sending 'D' means number, no error.
          # Client sebding 'R' means number, client error.
          # Both cases involve numbers, so send back an overwrite delta.
          output.append("D:" + text + "\n")
        else:
          # Client sending 'd' means text, no error.
          # Client sending 'r' means text, client error.
          # Both cases involve text, so send back a merge delta.
          output.append("d:" + text + "\n")
        logging.info("Sent '%s' delta: '%s %s'" %
                     (text, viewobj.username, viewobj.filename))
      else:
        # Error; server could not parse client's delta.
        # Send a raw dump of the text.  Force overwrite of client.
        value = mastertext
        value = value.encode("utf-8")
        value = urllib.quote(value, "!~*'();/?:@&=+$,# ")
        output.append("R:" + value + "\n")
        logging.info("Sent %db raw text: '%s %s'" %
                     (len(value), viewobj.username, viewobj.filename))

      if viewobj.mytext != mastertext:
        viewobj.mytext = mastertext
        viewobj.changed = True

      if viewobj.changed:
        logging.debug("Saving %db ViewObj: '%s %s'" %
                      (len(viewobj.mytext), viewobj.username, viewobj.filename))
        viewobj.put()
        viewobj.changed = False

  return ''.join(output)


if __name__ == '__main__':
  main()
