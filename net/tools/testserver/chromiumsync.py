#!/usr/bin/python2.4
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""An implementation of the server side of the Chromium sync protocol.

The details of the protocol are described mostly by comments in the protocol
buffer definition at chrome/browser/sync/protocol/sync.proto.
"""

import operator
import random
import threading

import autofill_specifics_pb2
import bookmark_specifics_pb2
import extension_specifics_pb2
import nigori_specifics_pb2
import password_specifics_pb2
import preference_specifics_pb2
import theme_specifics_pb2
import typed_url_specifics_pb2
import sync_pb2

# An enumeration of the various kinds of data that can be synced.
# Over the wire, this enumeration is not used: a sync object's type is
# inferred by which EntitySpecifics extension it has.  But in the context
# of a program, it is useful to have an enumeration.
ALL_TYPES = (
    TOP_LEVEL,  # The type of the 'Google Chrome' folder.
    AUTOFILL,
    BOOKMARK,
    EXTENSIONS,
    NIGORI,
    PASSWORD,
    PREFERENCE,
    # SESSION,
    THEME,
    TYPED_URL) = range(9)

# Given a sync type from ALL_TYPES, find the extension token corresponding
# to that datatype.  Note that TOP_LEVEL has no such token.
SYNC_TYPE_TO_EXTENSION = {
    AUTOFILL: autofill_specifics_pb2.autofill,
    BOOKMARK: bookmark_specifics_pb2.bookmark,
    EXTENSIONS: extension_specifics_pb2.extension,
    NIGORI: nigori_specifics_pb2.nigori,
    PASSWORD: password_specifics_pb2.password,
    PREFERENCE: preference_specifics_pb2.preference,
    # SESSION: session_specifics_pb2.session,     # Disabled
    THEME: theme_specifics_pb2.theme,
    TYPED_URL: typed_url_specifics_pb2.typed_url,
    }

# The parent ID used to indicate a top-level node.
ROOT_ID = '0'

def GetEntryType(entry):
  """Extract the sync type from a SyncEntry.

  Args:
    entry: A SyncEntity protobuf object whose type to determine.
  Returns:
    A value from ALL_TYPES if the entry's type can be determined, or None
    if the type cannot be determined.
  """
  if entry.server_defined_unique_tag == 'google_chrome':
    return TOP_LEVEL
  entry_types = GetEntryTypesFromSpecifics(entry.specifics)
  if not entry_types:
    return None
  # It is presupposed that the entry has at most one specifics extension
  # present.  If there is more than one, either there's a bug, or else
  # the caller should use GetEntryTypes.
  if len(entry_types) > 1:
    raise 'GetEntryType called with multiple extensions present.'
  return entry_types[0]

def GetEntryTypesFromSpecifics(specifics):
  """Determine the sync types indicated by an EntitySpecifics's extension(s).

  If the specifics have more than one recognized extension (as commonly
  happens with the requested_types field of GetUpdatesMessage), all types
  will be returned.  Callers must handle the possibility of the returned
  value having more than one item.

  Args:
    specifics: A EntitySpecifics protobuf message whose extensions to
      enumerate.
  Returns:
    A list of the sync types (values from ALL_TYPES) assocated with each
    recognized extension of the specifics message.
  """
  entry_types = []
  for data_type, extension in SYNC_TYPE_TO_EXTENSION.iteritems():
    if specifics.HasExtension(extension):
      entry_types.append(data_type)
  return entry_types

def GetRequestedTypes(get_updates_message):
  """Determine the sync types requested by a client GetUpdates operation."""
  types = GetEntryTypesFromSpecifics(
      get_updates_message.requested_types)
  if types:
    types.append(TOP_LEVEL)
  return types

def GetDefaultEntitySpecifics(data_type):
  """Get an EntitySpecifics having a sync type's default extension value.
  """
  specifics = sync_pb2.EntitySpecifics()
  if data_type in SYNC_TYPE_TO_EXTENSION:
    extension_handle = SYNC_TYPE_TO_EXTENSION[data_type]
    specifics.Extensions[extension_handle].SetInParent()
  return specifics

def DeepCopyOfProto(proto):
  """Return a deep copy of a protocol buffer."""
  new_proto = type(proto)()
  new_proto.MergeFrom(proto)
  return new_proto


class PermanentItem(object):
  """A specification of one server-created permanent item.

  Attributes:
    tag: A known-to-the-client value that uniquely identifies a server-created
      permanent item.
    name: The human-readable display name for this item.
    parent_tag: The tag of the permanent item's parent.  If ROOT_ID, indicates
      a top-level item.  Otherwise, this must be the tag value of some other
      server-created permanent item.
    sync_type: A value from ALL_TYPES, giving the datatype of this permanent
      item.  This controls which types of client GetUpdates requests will
      cause the permanent item to be created and returned.
  """

  def __init__(self, tag, name, parent_tag, sync_type):
    self.tag = tag
    self.name = name
    self.parent_tag = parent_tag
    self.sync_type = sync_type

class SyncDataModel(object):
  """Models the account state of one sync user.
  """
  _BATCH_SIZE = 100

  # Specify all the permanent items that a model might need.
  _PERMANENT_ITEM_SPECS = [
      PermanentItem('google_chrome', name='Google Chrome',
                    parent_tag=ROOT_ID, sync_type=TOP_LEVEL),
      PermanentItem('google_chrome_bookmarks', name='Bookmarks',
                    parent_tag='google_chrome', sync_type=BOOKMARK),
      PermanentItem('bookmark_bar', name='Bookmark Bar',
                    parent_tag='google_chrome_bookmarks', sync_type=BOOKMARK),
      PermanentItem('other_bookmarks', name='Other Bookmarks',
                    parent_tag='google_chrome_bookmarks', sync_type=BOOKMARK),
      PermanentItem('google_chrome_preferences', name='Preferences',
                    parent_tag='google_chrome', sync_type=PREFERENCE),
      PermanentItem('google_chrome_autofill', name='Autofill',
                    parent_tag='google_chrome', sync_type=AUTOFILL),
      PermanentItem('google_chrome_extensions', name='Extensions',
                    parent_tag='google_chrome', sync_type=EXTENSIONS),
      PermanentItem('google_chrome_passwords', name='Passwords',
                    parent_tag='google_chrome', sync_type=PASSWORD),
      # TODO(rsimha): Disabled since the protocol does not support it yet.
      # PermanentItem('google_chrome_sessions', name='Sessions',
      #               parent_tag='google_chrome', SESSION),
      PermanentItem('google_chrome_themes', name='Themes',
                    parent_tag='google_chrome', sync_type=THEME),
      PermanentItem('google_chrome_typed_urls', name='Typed URLs',
                    parent_tag='google_chrome', sync_type=TYPED_URL),
      PermanentItem('google_chrome_nigori', name='Nigori',
                    parent_tag='google_chrome', sync_type=NIGORI),
      ]

  def __init__(self):
    self._version = 0

    # Monotonically increasing version number.  The next object change will
    # take on this value + 1.
    self._entries = {}

    # TODO(nick): uuid.uuid1() is better, but python 2.5 only.
    self.store_birthday = '%0.30f' % random.random()

  def _SaveEntry(self, entry):
    """Insert or update an entry in the change log, and give it a new version.

    The ID fields of this entry are assumed to be valid server IDs.  This
    entry will be updated with a new version number and sync_timestamp.

    Args:
      entry: The entry to be added or updated.
    """
    self._version = self._version + 1
    entry.version = self._version
    entry.sync_timestamp = self._version

    # Preserve the originator info, which the client is not required to send
    # when updating.
    base_entry = self._entries.get(entry.id_string)
    if base_entry:
      entry.originator_cache_guid = base_entry.originator_cache_guid
      entry.originator_client_item_id = base_entry.originator_client_item_id

    self._entries[entry.id_string] = DeepCopyOfProto(entry)

  def _ServerTagToId(self, tag):
    """Determine the server ID from a server-unique tag.

    The resulting value is guaranteed not to collide with the other ID
    generation methods.

    Args:
      tag: The unique, known-to-the-client tag of a server-generated item.
    """
    if tag and tag != ROOT_ID:
      return '<server tag>%s' % tag
    else:
      return tag

  def _ClientTagToId(self, tag):
    """Determine the server ID from a client-unique tag.

    The resulting value is guaranteed not to collide with the other ID
    generation methods.

    Args:
      tag: The unique, opaque-to-the-server tag of a client-tagged item.
    """
    return '<client tag>%s' % tag

  def _ClientIdToId(self, client_guid, client_item_id):
    """Compute a unique server ID from a client-local ID tag.

    The resulting value is guaranteed not to collide with the other ID
    generation methods.

    Args:
      client_guid: A globally unique ID that identifies the client which
        created this item.
      client_item_id: An ID that uniquely identifies this item on the client
        which created it.
    """
    # Using the client ID info is not required here (we could instead generate
    # a random ID), but it's useful for debugging.
    return '<server ID originally>%s/%s' % (client_guid, client_item_id)

  def _WritePosition(self, entry, parent_id, prev_id=None):
    """Convert from a relative position into an absolute, numeric position.

    Clients specify positions using the predecessor-based references; the
    server stores and reports item positions using sparse integer values.
    This method converts from the former to the latter.

    Args:
      entry: The entry for which to compute a position.  Its ID field are
        assumed to be server IDs.  This entry will have its parent_id_string
        and position_in_parent fields updated; its insert_after_item_id field
        will be cleared.
      parent_id: The ID of the entry intended as the new parent.
      prev_id: The ID of the entry intended as the new predecessor.  If this
        is None, or an ID of an object which is not a child of the new parent,
        the entry will be positioned at the end (right) of the ordering.  If
        the empty ID (''), this will be positioned at the front (left) of the
        ordering.  Otherwise, the entry will be given a position_in_parent
        value placing it just after (to the right of) the new predecessor.
    """
    PREFERRED_GAP = 2 ** 20
    # Compute values at the beginning or end.
    def ExtendRange(current_limit_entry, sign_multiplier):
      if current_limit_entry.id_string == entry.id_string:
        step = 0
      else:
        step = sign_multiplier * PREFERRED_GAP
      return current_limit_entry.position_in_parent + step

    siblings = [x for x in self._entries.values()
                if x.parent_id_string == parent_id and not x.deleted]
    siblings = sorted(siblings, key=operator.attrgetter('position_in_parent'))
    if prev_id == entry.id_string:
      prev_id = ''
    if not siblings:
      # First item in this container; start in the middle.
      entry.position_in_parent = 0
    elif prev_id == '':
      # A special value in the protocol.  Insert at first position.
      entry.position_in_parent = ExtendRange(siblings[0], -1)
    else:
      # Consider items along with their successors.
      for a, b in zip(siblings, siblings[1:]):
        if a.id_string != prev_id:
          continue
        elif b.id_string == entry.id_string:
          # We're already in place; don't change anything.
          entry.position_in_parent = b.position_in_parent
        else:
          # Interpolate new position between two others.
          entry.position_in_parent = (
              a.position_in_parent * 7 + b.position_in_parent) / 8
        break
      else:
        # Insert at end. Includes the case where prev_id is None.
        entry.position_in_parent = ExtendRange(siblings[-1], +1)

    entry.parent_id_string = parent_id
    entry.ClearField('insert_after_item_id')

  def _ItemExists(self, id_string):
    """Determine whether an item exists in the changelog."""
    return id_string in self._entries

  def _CreatePermanentItem(self, spec):
    """Create one permanent item from its spec, if it doesn't exist.

    The resulting item is added to the changelog.

    Args:
      spec: A PermanentItem object holding the properties of the item to create.
    """
    id_string = self._ServerTagToId(spec.tag)
    if self._ItemExists(id_string):
      return
    print 'Creating permanent item: %s' % spec.name
    entry = sync_pb2.SyncEntity()
    entry.id_string = id_string
    entry.non_unique_name = spec.name
    entry.name = spec.name
    entry.server_defined_unique_tag = spec.tag
    entry.folder = True
    entry.deleted = False
    entry.specifics.CopyFrom(GetDefaultEntitySpecifics(spec.sync_type))
    self._WritePosition(entry, self._ServerTagToId(spec.parent_tag))
    self._SaveEntry(entry)

  def _CreatePermanentItems(self, requested_types):
    """Ensure creation of all permanent items for a given set of sync types.

    Args:
      requested_types: A list of sync data types from ALL_TYPES.
        Permanent items of only these types will be created.
    """
    for spec in self._PERMANENT_ITEM_SPECS:
      if spec.sync_type in requested_types:
        self._CreatePermanentItem(spec)

  def GetChangesFromTimestamp(self, requested_types, timestamp):
    """Get entries which have changed since a given timestamp, oldest first.

    The returned entries are limited to being _BATCH_SIZE many.  The entries
    are returned in strict version order.

    Args:
      requested_types: A list of sync data types from ALL_TYPES.
        Only items of these types will be retrieved; others will be filtered
        out.
      timestamp: A timestamp / version number.  Only items that have changed
        more recently than this value will be retrieved; older items will
        be filtered out.
    Returns:
      A tuple of (version, entries).  Version is a new timestamp value, which
      should be used as the starting point for the next query.  Entries is the
      batch of entries meeting the current timestamp query.
    """
    if timestamp == 0:
      self._CreatePermanentItems(requested_types)
    change_log = sorted(self._entries.values(),
                        key=operator.attrgetter('version'))
    new_changes = [x for x in change_log if x.version > timestamp]
    # Pick batch_size new changes, and then filter them.  This matches
    # the RPC behavior of the production sync server.
    batch = new_changes[:self._BATCH_SIZE]
    if not batch:
      # Client is up to date.
      return (timestamp, [])

    # Restrict batch to requested types.  Tombstones are untyped
    # and will always get included.
    filtered = []
    for x in batch:
      if (GetEntryType(x) in requested_types) or x.deleted:
        filtered.append(DeepCopyOfProto(x))
    # The new client timestamp is the timestamp of the last item in the
    # batch, even if that item was filtered out.
    return (batch[-1].version, filtered)

  def _CheckVersionForCommit(self, entry):
    """Perform an optimistic concurrency check on the version number.

    Clients are only allowed to commit if they report having seen the most
    recent version of an object.

    Args:
      entry: A sync entity from the client.  It is assumed that ID fields
        have been converted to server IDs.
    Returns:
      A boolean value indicating whether the client's version matches the
      newest server version for the given entry.
    """
    if entry.id_string in self._entries:
      if (self._entries[entry.id_string].version != entry.version and
          not self._entries[entry.id_string].deleted):
        # Version mismatch that is not a tombstone recreation.
        return False
    else:
      if entry.version != 0:
        # Edit to an item that does not exist.
        return False
    return True

  def _CheckParentIdForCommit(self, entry):
    """Check that the parent ID referenced in a SyncEntity actually exists.

    Args:
      entry: A sync entity from the client.  It is assumed that ID fields
        have been converted to server IDs.
    Returns:
      A boolean value indicating whether the entity's parent ID is an object
      that actually exists (and is not deleted) in the current account state.
    """
    if entry.parent_id_string == ROOT_ID:
      # This is generally allowed.
      return True
    if entry.parent_id_string not in self._entries:
      print 'Warning: Client sent unknown ID.  Should never happen.'
      return False
    if entry.parent_id_string == entry.id_string:
      print 'Warning: Client sent circular reference.  Should never happen.'
      return False
    if self._entries[entry.parent_id_string].deleted:
      # This can happen in a race condition between two clients.
      return False
    if not self._entries[entry.parent_id_string].folder:
      print 'Warning: Client sent non-folder parent.  Should never happen.'
      return False
    return True

  def _RewriteIdsAsServerIds(self, entry, cache_guid, commit_session):
    """Convert ID fields in a client sync entry to server IDs.

    A commit batch sent by a client may contain new items for which the
    server has not generated IDs yet.  And within a commit batch, later
    items are allowed to refer to earlier items.  This method will
    generate server IDs for new items, as well as rewrite references
    to items whose server IDs were generated earlier in the batch.

    Args:
      entry: The client sync entry to modify.
      cache_guid: The globally unique ID of the client that sent this
        commit request.
      commit_session: A dictionary mapping the original IDs to the new server
        IDs, for any items committed earlier in the batch.
    """
    if entry.version == 0:
      if entry.HasField('client_defined_unique_tag'):
        # When present, this should determine the item's ID.
        new_id = self._ClientTagToId(entry.client_defined_unique_tag)
      else:
        new_id = self._ClientIdToId(cache_guid, entry.id_string)
        entry.originator_cache_guid = cache_guid
        entry.originator_client_item_id = entry.id_string
      commit_session[entry.id_string] = new_id  # Remember the remapping.
      entry.id_string = new_id
    if entry.parent_id_string in commit_session:
      entry.parent_id_string = commit_session[entry.parent_id_string]
    if entry.insert_after_item_id in commit_session:
      entry.insert_after_item_id = commit_session[entry.insert_after_item_id]

  def CommitEntry(self, entry, cache_guid, commit_session):
    """Attempt to commit one entry to the user's account.

    Args:
      entry: A SyncEntity protobuf representing desired object changes.
      cache_guid: A string value uniquely identifying the client; this
        is used for ID generation and will determine the originator_cache_guid
        if the entry is new.
      commit_session: A dictionary mapping client IDs to server IDs for any
        objects committed earlier this session.  If the entry gets a new ID
        during commit, the change will be recorded here.
    Returns:
      A SyncEntity reflecting the post-commit value of the entry, or None
      if the entry was not committed due to an error.
    """
    entry = DeepCopyOfProto(entry)

    # Generate server IDs for this entry, and write generated server IDs
    # from earlier entries into the message's fields, as appropriate.  The
    # ID generation state is stored in 'commit_session'.
    self._RewriteIdsAsServerIds(entry, cache_guid, commit_session)

    # Perform the optimistic concurrency check on the entry's version number.
    # Clients are not allowed to commit unless they indicate that they've seen
    # the most recent version of an object.
    if not self._CheckVersionForCommit(entry):
      return None

    # Check the validity of the parent ID; it must exist at this point.
    # TODO(nick): Implement cycle detection and resolution.
    if not self._CheckParentIdForCommit(entry):
      return None

    # At this point, the commit is definitely going to happen.

    # Deletion works by storing a limited record for an entry, called a
    # tombstone.  A sync server must track deleted IDs forever, since it does
    # not keep track of client knowledge (there's no deletion ACK event).
    if entry.deleted:
      # Only the ID, version and deletion state are preserved on a tombstone.
      # TODO(nick): Does the production server not preserve the type?  Not
      # doing so means that tombstones cannot be filtered based on
      # requested_types at GetUpdates time.
      tombstone = sync_pb2.SyncEntity()
      tombstone.id_string = entry.id_string
      tombstone.deleted = True
      tombstone.name = ''  # 'name' is a required field; we're stuck with it.
      entry = tombstone
    else:
      # Comments in sync.proto detail how the representation of positional
      # ordering works: the 'insert_after_item_id' field specifies a
      # predecessor during Commit operations, but the 'position_in_parent'
      # field provides an absolute ordering in GetUpdates contexts.  Here
      # we convert from the former to the latter.  Specifically, we'll
      # generate a numeric position placing the item just after the object
      # identified by 'insert_after_item_id', and then clear the
      # 'insert_after_item_id' field so that it's not sent back to the client
      # during later GetUpdates requests.
      if entry.HasField('insert_after_item_id'):
        self._WritePosition(entry, entry.parent_id_string,
                            entry.insert_after_item_id)
      else:
        self._WritePosition(entry, entry.parent_id_string)

    # Preserve the originator info, which the client is not required to send
    # when updating.
    base_entry = self._entries.get(entry.id_string)
    if base_entry and not entry.HasField("originator_cache_guid"):
      entry.originator_cache_guid = base_entry.originator_cache_guid
      entry.originator_client_item_id = base_entry.originator_client_item_id

    # Commit the change.  This also updates the version number.
    self._SaveEntry(entry)
    # TODO(nick): Handle recursive deletion.
    return entry

class TestServer(object):
  """An object to handle requests for one (and only one) Chrome Sync account.

  TestServer consumes the sync command messages that are the outermost
  layers of the protocol, performs the corresponding actions on its
  SyncDataModel, and constructs an appropropriate response message.
  """

  def __init__(self):
    # The implementation supports exactly one account; its state is here.
    self.account = SyncDataModel()
    self.account_lock = threading.Lock()

  def HandleCommand(self, raw_request):
    """Decode and handle a sync command from a raw input of bytes.

    This is the main entry point for this class.  It is safe to call this
    method from multiple threads.

    Args:
      raw_request: An iterable byte sequence to be interpreted as a sync
        protocol command.
    Returns:
      A tuple (response_code, raw_response); the first value is an HTTP
      result code, while the second value is a string of bytes which is the
      serialized reply to the command.
    """
    self.account_lock.acquire()
    try:
      request = sync_pb2.ClientToServerMessage()
      request.MergeFromString(raw_request)
      contents = request.message_contents

      response = sync_pb2.ClientToServerResponse()
      response.error_code = sync_pb2.ClientToServerResponse.SUCCESS
      response.store_birthday = self.account.store_birthday

      if contents == sync_pb2.ClientToServerMessage.AUTHENTICATE:
        print 'Authenticate'
        # We accept any authentication token, and support only one account.
        # TODO(nick): Mock out the GAIA authentication as well; hook up here.
        response.authenticate.user.email = 'syncjuser@chromium'
        response.authenticate.user.display_name = 'Sync J User'
      elif contents == sync_pb2.ClientToServerMessage.COMMIT:
        print 'Commit'
        self.HandleCommit(request.commit, response.commit)
      elif contents == sync_pb2.ClientToServerMessage.GET_UPDATES:
        print ('GetUpdates from timestamp %d' %
            request.get_updates.from_timestamp)
        self.HandleGetUpdates(request.get_updates, response.get_updates)
      return (200, response.SerializeToString())
    finally:
      self.account_lock.release()

  def HandleCommit(self, commit_message, commit_response):
    """Respond to a Commit request by updating the user's account state.

    Commit attempts stop after the first error, returning a CONFLICT result
    for any unattempted entries.

    Args:
      commit_message: A sync_pb.CommitMessage protobuf holding the content
        of the client's request.
      commit_response: A sync_pb.CommitResponse protobuf into which a reply
        to the client request will be written.
    """
    commit_response.SetInParent()
    batch_failure = False
    session = {}  # Tracks ID renaming during the commit operation.
    guid = commit_message.cache_guid
    for entry in commit_message.entries:
      server_entry = None
      if not batch_failure:
        # Try to commit the change to the account.
        server_entry = self.account.CommitEntry(entry, guid, session)

      # An entryresponse is returned in both success and failure cases.
      reply = commit_response.entryresponse.add()
      if not server_entry:
        reply.response_type = sync_pb2.CommitResponse.CONFLICT
        reply.error_message = 'Conflict.'
        batch_failure = True  # One failure halts the batch.
      else:
        reply.response_type = sync_pb2.CommitResponse.SUCCESS
        # These are the properties that the server is allowed to override
        # during commit; the client wants to know their values at the end
        # of the operation.
        reply.id_string = server_entry.id_string
        if not server_entry.deleted:
          reply.parent_id_string = server_entry.parent_id_string
          reply.position_in_parent = server_entry.position_in_parent
          reply.version = server_entry.version
          reply.name = server_entry.name
          reply.non_unique_name = server_entry.non_unique_name

  def HandleGetUpdates(self, update_request, update_response):
    """Respond to a GetUpdates request by querying the user's account.

    Args:
      update_request: A sync_pb.GetUpdatesMessage protobuf holding the content
        of the client's request.
      update_response: A sync_pb.GetUpdatesResponse protobuf into which a reply
        to the client request will be written.
    """
    update_response.SetInParent()
    requested_types = GetRequestedTypes(update_request)
    new_timestamp, entries = self.account.GetChangesFromTimestamp(
        requested_types, update_request.from_timestamp)

    # If the client is up to date, we are careful not to set the
    # new_timestamp field.
    if new_timestamp != update_request.from_timestamp:
      update_response.new_timestamp = new_timestamp
      for e in entries:
        reply = update_response.entries.add()
        reply.CopyFrom(e)
