# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

{
  'variables': {
    'chromium_code': 1,
  },
  'targets': [
    # The core sync library.
    #
    # TODO(akalin): Rename this to something like 'sync_core' and
    # reserve the 'sync' name for the overarching library that clients
    # should depend on.
    {
      'target_name': 'sync',
      'type': 'static_library',
      'variables': { 'enable_wexit_time_destructors': 1, },
      'include_dirs': [
        '..',
      ],
      'dependencies': [
        '../base/base.gyp:base',
        '../build/temp_gyp/googleurl.gyp:googleurl',
        '../crypto/crypto.gyp:crypto',
        '../net/net.gyp:net',
        '../sql/sql.gyp:sql',
        'protocol/sync_proto.gyp:sync_proto',
      ],
      'export_dependent_settings': [
        '../base/base.gyp:base',
        '../build/temp_gyp/googleurl.gyp:googleurl',
        '../crypto/crypto.gyp:crypto',
        '../net/net.gyp:net',
        '../sql/sql.gyp:sql',
        'protocol/sync_proto.gyp:sync_proto',
      ],
      'sources': [
        'engine/apply_updates_command.cc',
        'engine/apply_updates_command.h',
        'engine/build_commit_command.cc',
        'engine/build_commit_command.h',
        'engine/cleanup_disabled_types_command.cc',
        'engine/cleanup_disabled_types_command.h',
        'engine/clear_data_command.cc',
        'engine/clear_data_command.h',
        'engine/conflict_resolver.cc',
        'engine/conflict_resolver.h',
        'engine/download_updates_command.cc',
        'engine/download_updates_command.h',
        'engine/get_commit_ids_command.cc',
        'engine/get_commit_ids_command.h',
        'engine/model_changing_syncer_command.cc',
        'engine/model_changing_syncer_command.h',
        'engine/model_safe_worker.cc',
        'engine/model_safe_worker.h',
        'engine/passive_model_worker.cc',
        'engine/passive_model_worker.h',
        'engine/net/server_connection_manager.cc',
        'engine/net/server_connection_manager.h',
        'engine/net/url_translator.cc',
        'engine/net/url_translator.h',
        'engine/nigori_util.cc',
        'engine/nigori_util.h',
        'engine/nudge_source.cc',
        'engine/nudge_source.h',
        'engine/polling_constants.cc',
        'engine/polling_constants.h',
        'engine/post_commit_message_command.cc',
        'engine/post_commit_message_command.h',
        'engine/process_commit_response_command.cc',
        'engine/process_commit_response_command.h',
        'engine/process_updates_command.cc',
        'engine/process_updates_command.h',
        'engine/resolve_conflicts_command.cc',
        'engine/resolve_conflicts_command.h',
        'engine/store_timestamps_command.cc',
        'engine/store_timestamps_command.h',
        'engine/syncer.cc',
        'engine/syncer.h',
        'engine/syncer_command.cc',
        'engine/syncer_command.h',
        'engine/syncer_proto_util.cc',
        'engine/syncer_proto_util.h',
        'engine/sync_scheduler.cc',
        'engine/sync_scheduler.h',
        'engine/syncer_types.cc',
        'engine/syncer_types.h',
        'engine/syncer_util.cc',
        'engine/syncer_util.h',
        'engine/syncproto.h',
        'engine/update_applicator.cc',
        'engine/update_applicator.h',
        'engine/verify_updates_command.cc',
        'engine/verify_updates_command.h',
        'js/js_arg_list.cc',
        'js/js_arg_list.h',
        'js/js_backend.h',
        'js/js_controller.h',
        'js/js_event_details.cc',
        'js/js_event_details.h',
        'js/js_event_handler.h',
        'js/js_reply_handler.h',
        'js/sync_js_controller.cc',
        'js/sync_js_controller.h',
        'protocol/proto_enum_conversions.cc',
        'protocol/proto_enum_conversions.h',
        'protocol/proto_value_conversions.cc',
        'protocol/proto_value_conversions.h',
        'protocol/service_constants.h',
        'protocol/sync_protocol_error.cc',
        'protocol/sync_protocol_error.h',
        'sessions/debug_info_getter.h',
        'sessions/ordered_commit_set.cc',
        'sessions/ordered_commit_set.h',
        'sessions/session_state.cc',
        'sessions/session_state.h',
        'sessions/status_controller.cc',
        'sessions/status_controller.h',
        'sessions/sync_session.cc',
        'sessions/sync_session.h',
        'sessions/sync_session_context.cc',
        'sessions/sync_session_context.h',
        'syncable/blob.h',
        'syncable/directory_backing_store.cc',
        'syncable/directory_backing_store.h',
        'syncable/directory_change_delegate.h',
        'syncable/dir_open_result.h',
        'syncable/in_memory_directory_backing_store.cc',
        'syncable/in_memory_directory_backing_store.h',
        'syncable/model_type.cc',
        'syncable/model_type.h',
        'syncable/model_type_payload_map.cc',
        'syncable/model_type_payload_map.h',
        'syncable/on_disk_directory_backing_store.cc',
        'syncable/on_disk_directory_backing_store.h',
        'syncable/syncable.cc',
        'syncable/syncable_changes_version.h',
        'syncable/syncable_columns.h',
        'syncable/syncable_enum_conversions.cc',
        'syncable/syncable_enum_conversions.h',
        'syncable/syncable.h',
        'syncable/syncable_id.cc',
        'syncable/syncable_id.h',
        'syncable/syncable-inl.h',
        'syncable/transaction_observer.h',
        'util/cryptographer.cc',
        'util/cryptographer.h',

        # TODO(akalin): Figure out a better place to put
        # data_encryption_win*; it's also used by autofill.
        'util/data_encryption_win.cc',
        'util/data_encryption_win.h',

        'util/data_type_histogram.h',
        'util/encryptor.h',
        'util/enum_set.h',
        'util/extensions_activity_monitor.cc',
        'util/extensions_activity_monitor.h',
        'util/get_session_name.cc',
        'util/get_session_name.h',
        'util/get_session_name_mac.mm',
        'util/get_session_name_mac.h',
        'util/get_session_name_win.cc',
        'util/get_session_name_win.h',
        'util/immutable.h',
        'util/logging.cc',
        'util/logging.h',
        'util/nigori.cc',
        'util/nigori.h',
        'util/report_unrecoverable_error_function.h',
        'util/syncer_error.cc',
        'util/syncer_error.h',
        'util/time.cc',
        'util/time.h',
        'util/unrecoverable_error_handler.h',
        'util/unrecoverable_error_info.h',
        'util/unrecoverable_error_info.cc',
        'util/weak_handle.cc',
        'util/weak_handle.h',
      ],
    },

    # Test support files for the 'sync' target.
    {
      'target_name': 'test_support_sync',
      'type': 'static_library',
      'variables': { 'enable_wexit_time_destructors': 1, },
      'include_dirs': [
        '..',
      ],
      'dependencies': [
        '../base/base.gyp:base',
        '../testing/gmock.gyp:gmock',
        '../testing/gtest.gyp:gtest',
        'sync',
      ],
      'export_dependent_settings': [
        '../base/base.gyp:base',
        '../testing/gmock.gyp:gmock',
        '../testing/gtest.gyp:gtest',
        'sync',
      ],
      'sources': [
        'js/js_test_util.cc',
        'js/js_test_util.h',
        'sessions/test_util.cc',
        'sessions/test_util.h',
        'syncable/model_type_test_util.cc',
        'syncable/model_type_test_util.h',
        'syncable/syncable_mock.cc',
        'syncable/syncable_mock.h',
        'test/fake_encryptor.cc',
        'test/fake_encryptor.h',
        'test/fake_extensions_activity_monitor.cc',
        'test/fake_extensions_activity_monitor.h',
        'test/null_directory_change_delegate.cc',
        'test/null_directory_change_delegate.h',
        'test/null_transaction_observer.cc',
        'test/null_transaction_observer.h',
        'test/engine/test_directory_setter_upper.cc',
        'test/engine/test_directory_setter_upper.h',
        'test/engine/fake_model_safe_worker_registrar.cc',
        'test/engine/fake_model_safe_worker_registrar.h',
        'test/engine/fake_model_worker.cc',
        'test/engine/fake_model_worker.h',
        'test/engine/mock_connection_manager.cc',
        'test/engine/mock_connection_manager.h',
        'test/engine/syncer_command_test.cc',
        'test/engine/syncer_command_test.h',
        'test/engine/test_id_factory.h',
        'test/engine/test_syncable_utils.cc',
        'test/engine/test_syncable_utils.h',
        'test/sessions/test_scoped_session_event_listener.h',
        'test/test_directory_backing_store.cc',
        'test/test_directory_backing_store.h',
        'util/test_unrecoverable_error_handler.cc',
        'util/test_unrecoverable_error_handler.h',
      ],
    },

    # Unit tests for the 'sync' target.  This cannot be a static
    # library because the unit test files have to be compiled directly
    # into the executable, so we push the target files to the
    # depending executable target via direct_dependent_settings.
    {
      'target_name': 'sync_tests',
      'type': 'none',
      'dependencies': [
        '../base/base.gyp:base',
        '../base/base.gyp:test_support_base',
        '../testing/gmock.gyp:gmock',
        '../testing/gtest.gyp:gtest',
        'sync',
        'test_support_sync',
      ],
      'export_dependent_settings': [
        '../base/base.gyp:base',
        '../base/base.gyp:test_support_base',
        '../testing/gmock.gyp:gmock',
        '../testing/gtest.gyp:gtest',
        'sync',
        'test_support_sync',
      ],
      'direct_dependent_settings': {
        'variables': { 'enable_wexit_time_destructors': 1, },
        'include_dirs': [
          '..',
        ],
        'sources': [
          'engine/apply_updates_command_unittest.cc',
          'engine/build_commit_command_unittest.cc',
          'engine/clear_data_command_unittest.cc',
          'engine/cleanup_disabled_types_command_unittest.cc',
          'engine/download_updates_command_unittest.cc',
          'engine/model_changing_syncer_command_unittest.cc',
          'engine/model_safe_worker_unittest.cc',
          'engine/nigori_util_unittest.cc',
          'engine/process_commit_response_command_unittest.cc',
          'engine/process_updates_command_unittest.cc',
          'engine/resolve_conflicts_command_unittest.cc',
          'engine/syncer_proto_util_unittest.cc',
          'engine/sync_scheduler_unittest.cc',
          'engine/sync_scheduler_whitebox_unittest.cc',
          'engine/syncer_unittest.cc',
          'engine/syncproto_unittest.cc',
          'engine/verify_updates_command_unittest.cc',
          'js/js_arg_list_unittest.cc',
          'js/js_event_details_unittest.cc',
          'js/sync_js_controller_unittest.cc',
          'protocol/proto_enum_conversions_unittest.cc',
          'protocol/proto_value_conversions_unittest.cc',
          'sessions/ordered_commit_set_unittest.cc',
          'sessions/session_state_unittest.cc',
          'sessions/status_controller_unittest.cc',
          'sessions/sync_session_context_unittest.cc',
          'sessions/sync_session_unittest.cc',
          'syncable/directory_backing_store_unittest.cc',
          'syncable/model_type_payload_map_unittest.cc',
          'syncable/model_type_unittest.cc',
          'syncable/syncable_enum_conversions_unittest.cc',
          'syncable/syncable_id_unittest.cc',
          'syncable/syncable_unittest.cc',
          'util/cryptographer_unittest.cc',
          'util/data_encryption_win_unittest.cc',
          'util/data_type_histogram_unittest.cc',
          'util/enum_set_unittest.cc',
          'util/get_session_name_unittest.cc',
          'util/immutable_unittest.cc',
          'util/nigori_unittest.cc',
          'util/protobuf_unittest.cc',
          'util/weak_handle_unittest.cc',
        ],
      },
    },

    # The unit test executable for sync tests.  Currently this isn't
    # automatically run, as there is already a sync_unit_tests
    # executable in chrome.gyp; this is just to make sure that all the
    # link-time dependencies for the files in the targets above
    # resolve.
    #
    # TODO(akalin): Rename this to sync_unit_tests once we've moved
    # everything from chrome.gyp.
    #
    # TODO(akalin): Make base.gyp have a test_main target that
    # includes run_all_unittests.cc and the possible tcmalloc
    # dependency and use that everywhere.
    {
      'target_name': 'sync_unit_tests_canary',
      'type': 'executable',
      'sources': [
        '../base/test/run_all_unittests.cc',
      ],
      'dependencies': [
        'sync_tests',
      ],

      # TODO(akalin): This is needed because histogram.cc uses
      # leak_annotations.h, which pulls this in.  Make 'base'
      # propagate this dependency.
      'conditions': [
        ['OS=="linux" and linux_use_tcmalloc==1', {
          'dependencies': [
            '../base/allocator/allocator.gyp:allocator',
          ],
        }],
      ],
    },
  ],
}
