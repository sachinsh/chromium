// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef PPAPI_SHARED_IMPL_RESOURCE_H_
#define PPAPI_SHARED_IMPL_RESOURCE_H_

#include <stddef.h>  // For NULL.

#include <string>

#include "base/basictypes.h"
#include "base/memory/ref_counted.h"
#include "ppapi/c/pp_instance.h"
#include "ppapi/c/pp_resource.h"
#include "ppapi/c/dev/ppb_console_dev.h"
#include "ppapi/shared_impl/host_resource.h"

// All resource types should be added here. This implements our hand-rolled
// RTTI system since we don't compile with "real" RTTI.
#define FOR_ALL_PPAPI_RESOURCE_APIS(F) \
  F(PPB_Audio_API) \
  F(PPB_AudioConfig_API) \
  F(PPB_AudioInput_API) \
  F(PPB_AudioInputTrusted_API) \
  F(PPB_AudioTrusted_API) \
  F(PPB_Broker_API) \
  F(PPB_BrowserFont_Trusted_API) \
  F(PPB_Buffer_API) \
  F(PPB_BufferTrusted_API) \
  F(PPB_DeviceRef_API) \
  F(PPB_DirectoryReader_API) \
  F(PPB_FileChooser_API) \
  F(PPB_FileIO_API) \
  F(PPB_FileRef_API) \
  F(PPB_FileSystem_API) \
  F(PPB_Find_API) \
  F(PPB_Flash_Menu_API) \
  F(PPB_Flash_MessageLoop_API) \
  F(PPB_Graphics2D_API) \
  F(PPB_Graphics3D_API) \
  F(PPB_HostResolver_Private_API) \
  F(PPB_ImageData_API) \
  F(PPB_InputEvent_API) \
  F(PPB_LayerCompositor_API) \
  F(PPB_MessageLoop_API) \
  F(PPB_NetworkList_Private_API) \
  F(PPB_NetworkMonitor_Private_API) \
  F(PPB_PDFFont_API) \
  F(PPB_ResourceArray_API) \
  F(PPB_Scrollbar_API) \
  F(PPB_Talk_Private_API) \
  F(PPB_TCPServerSocket_Private_API) \
  F(PPB_TCPSocket_Private_API) \
  F(PPB_Transport_API) \
  F(PPB_UDPSocket_Private_API) \
  F(PPB_URLLoader_API) \
  F(PPB_URLRequestInfo_API) \
  F(PPB_URLResponseInfo_API) \
  F(PPB_VideoCapture_API) \
  F(PPB_VideoDecoder_API) \
  F(PPB_VideoLayer_API) \
  F(PPB_View_API) \
  F(PPB_WebSocket_API) \
  F(PPB_Widget_API) \
  F(PPB_X509Certificate_Private_API)

namespace ppapi {

// Forward declare all the resource APIs.
namespace thunk {
#define DECLARE_RESOURCE_CLASS(RESOURCE) class RESOURCE;
FOR_ALL_PPAPI_RESOURCE_APIS(DECLARE_RESOURCE_CLASS)
#undef DECLARE_RESOURCE_CLASS
}  // namespace thunk

// Resources have slightly different registration behaviors when the're an
// in-process ("impl") resource in the host (renderer) process, or when they're
// a proxied resource in the plugin process. This enum differentiates those
// cases.
enum ResourceObjectType {
  OBJECT_IS_IMPL,
  OBJECT_IS_PROXY
};

class PPAPI_SHARED_EXPORT Resource : public base::RefCounted<Resource> {
 public:
  // Constructor for impl and non-proxied, instance-only objects.
  //
  // For constructing "impl" (non-proxied) objects, this just takes the
  // associated instance, and generates a new resource ID. The host resource
  // will be the same as the newly-generated resource ID. For all objects in
  // the renderer (host) process, you'll use this constructor and call it with
  // OBJECT_IS_IMPL.
  //
  // For proxied objects, this will create an "instance-only" object which
  // lives only in the plugin and doesn't have a corresponding object in the
  // host. If you have a host resource ID, use the constructor below which
  // takes that HostResource value.
  explicit Resource(ResourceObjectType type, PP_Instance instance);

  // For constructing given a host resource.
  //
  // For OBJECT_IS_PROXY objects, this takes the resource generated in the host
  // side, stores it, and allocates a "local" resource ID for use in the
  // current process.
  //
  // For OBJECT_IS_IMPL, the host resource ID must be 0, since there should be
  // no host resource generated (impl objects should generate their own). The
  // reason for supporting this constructor at all for the IMPL case is that
  // some shared objects use a host resource for both modes to keep things the
  // same.
  explicit Resource(ResourceObjectType type,
                    const HostResource& host_resource);

  virtual ~Resource();

  PP_Instance pp_instance() const { return host_resource_.instance(); }

  // Returns the resource ID for this object in the current process without
  // adjusting the refcount. See also GetReference().
  PP_Resource pp_resource() const { return pp_resource_; }

  // Returns the host resource which identifies the resource in the host side
  // of the process in the case of proxied objects. For in-process objects,
  // this just identifies the in-process resource ID & instance.
  const HostResource& host_resource() { return host_resource_; }

  // Adds a ref on behalf of the plugin and returns the resource ID. This is
  // normally used when returning a resource to the plugin, where it's
  // expecting the returned resource to have ownership of a ref passed.
  // See also pp_resource() to avoid the AddRef.
  PP_Resource GetReference();

  // Called by the resource tracker when the last reference from the plugin
  // was released. For a few types of resources, the resource could still
  // stay alive if there are other references held by the PPAPI implementation
  // (possibly for callbacks and things).
  virtual void LastPluginRefWasDeleted();

  // Called by the resource tracker when the instance is going away but the
  // object is still alive (this is not the common case, since it requires
  // something in the implementation to be keeping a ref that keeps the
  // resource alive.
  //
  // You will want to override this if your resource does some kind of
  // background processing (like maybe network loads) on behalf of the plugin
  // and you want to stop that when the plugin is deleted.
  //
  // Be sure to call this version which clears the instance ID.
  virtual void InstanceWasDeleted();

  // Dynamic casting for this object. Returns the pointer to the given type if
  // it's supported. Derived classes override the functions they support to
  // return the interface.
  #define DEFINE_TYPE_GETTER(RESOURCE) \
    virtual thunk::RESOURCE* As##RESOURCE();
  FOR_ALL_PPAPI_RESOURCE_APIS(DEFINE_TYPE_GETTER)
  #undef DEFINE_TYPE_GETTER

  // Template-based dynamic casting. See specializations below.
  template <typename T> T* GetAs() { return NULL; }

 protected:
  // Logs a message to the console from this resource.
  void Log(PP_LogLevel_Dev level, const std::string& message);

 private:
  // See the getters above.
  PP_Resource pp_resource_;
  HostResource host_resource_;

  DISALLOW_IMPLICIT_CONSTRUCTORS(Resource);
};

// Template-based dynamic casting. These specializations forward to the
// AsXXX virtual functions to return whether the given type is supported.
#define DEFINE_RESOURCE_CAST(RESOURCE) \
  template<> inline thunk::RESOURCE* Resource::GetAs() { \
    return As##RESOURCE(); \
  }
FOR_ALL_PPAPI_RESOURCE_APIS(DEFINE_RESOURCE_CAST)
#undef DEFINE_RESOURCE_CAST

}  // namespace ppapi

#endif  // PPAPI_SHARED_IMPL_RESOURCE_H_
