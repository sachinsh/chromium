// Copyright (c) 2011 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "chrome/browser/ui/webui/chromeos/login/oobe_ui.h"

#include <string>

#include "base/logging.h"
#include "base/memory/ref_counted_memory.h"
#include "base/values.h"
#include "chrome/browser/browser_about_handler.h"
#include "chrome/browser/chromeos/accessibility_util.h"
#include "chrome/browser/chromeos/login/enterprise_enrollment_screen_actor.h"
#include "chrome/browser/chromeos/login/wizard_controller.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/webui/chrome_url_data_manager.h"
#include "chrome/browser/ui/webui/chromeos/login/base_screen_handler.h"
#include "chrome/browser/ui/webui/chromeos/login/enterprise_enrollment_screen_handler.h"
#include "chrome/browser/ui/webui/chromeos/login/eula_screen_handler.h"
#include "chrome/browser/ui/webui/chromeos/login/network_screen_handler.h"
#include "chrome/browser/ui/webui/chromeos/login/signin_screen_handler.h"
#include "chrome/browser/ui/webui/chromeos/login/update_screen_handler.h"
#include "chrome/browser/ui/webui/options/chromeos/user_image_source.h"
#include "chrome/browser/ui/webui/theme_source.h"
#include "chrome/common/jstemplate_builder.h"
#include "chrome/common/url_constants.h"
#include "content/browser/tab_contents/tab_contents.h"
#include "grit/browser_resources.h"
#include "grit/chromium_strings.h"
#include "grit/generated_resources.h"
#include "ui/base/l10n/l10n_util.h"
#include "ui/base/resource/resource_bundle.h"

namespace {

// JS API callbacks names.
const char kJsApiScreenStateInitialize[] = "screenStateInitialize";
const char kJsApiToggleAccessibility[] = "toggleAccessibility";

// Path for the enterprise enrollment gaia page hosting.
const char kEnterpriseEnrollmentGaiaLoginPath[] = "gaialogin";

}  // namespace

namespace chromeos {

class OobeUIHTMLSource : public ChromeURLDataManager::DataSource {
 public:
  explicit OobeUIHTMLSource(DictionaryValue* localized_strings);

  // Called when the network layer has requested a resource underneath
  // the path we registered.
  virtual void StartDataRequest(const std::string& path,
                                bool is_incognito,
                                int request_id);
  virtual std::string GetMimeType(const std::string&) const {
    return "text/html";
  }

 private:
  virtual ~OobeUIHTMLSource() {}

  scoped_ptr<DictionaryValue> localized_strings_;
  DISALLOW_COPY_AND_ASSIGN(OobeUIHTMLSource);
};

// CoreOobeHandler -------------------------------------------------------------

// The core handler for Javascript messages related to the "oobe" view.
class CoreOobeHandler : public BaseScreenHandler {
 public:
  explicit CoreOobeHandler(OobeUI* oobe_ui);
  virtual ~CoreOobeHandler();

  // BaseScreenHandler implementation:
  virtual void GetLocalizedStrings(base::DictionaryValue* localized_strings);
  virtual void Initialize();

  // WebUIMessageHandler implementation.
  virtual void RegisterMessages();

  // Show or hide OOBE UI.
  void ShowOobeUI(bool show);

  bool show_oobe_ui() const {
    return show_oobe_ui_;
  }

 private:
  // Handlers for JS WebUI messages.
  void OnInitialized(const ListValue* args);
  void OnToggleAccessibility(const ListValue* args);

  // Calls javascript to sync OOBE UI visibility with show_oobe_ui_.
  void UpdateOobeUIVisibility();

  // Owner of this handler.
  OobeUI* oobe_ui_;

  // True if we should show OOBE instead of login.
  bool show_oobe_ui_;

  DISALLOW_COPY_AND_ASSIGN(CoreOobeHandler);
};

// OobeUIHTMLSource -------------------------------------------------------

OobeUIHTMLSource::OobeUIHTMLSource(DictionaryValue* localized_strings)
    : DataSource(chrome::kChromeUIOobeHost, MessageLoop::current()),
      localized_strings_(localized_strings) {
}

void OobeUIHTMLSource::StartDataRequest(const std::string& path,
                                        bool is_incognito,
                                        int request_id) {
  std::string response;
  if (path.empty()) {
    static const base::StringPiece html(
        ResourceBundle::GetSharedInstance().GetRawDataResource(IDR_OOBE_HTML));
    response = jstemplate_builder::GetI18nTemplateHtml(
        html, localized_strings_.get());
  } else if (path == kEnterpriseEnrollmentGaiaLoginPath) {
    static const base::StringPiece html(
        ResourceBundle::GetSharedInstance().GetRawDataResource(
            IDR_GAIA_LOGIN_HTML));
    response = jstemplate_builder::GetI18nTemplateHtml(
        html, localized_strings_.get());
  }

  SendResponse(request_id, base::RefCountedString::TakeString(&response));
}

// CoreOobeHandler ------------------------------------------------------------

// Note that show_oobe_ui_ defaults to false because WizardController assumes
// OOBE UI is not visible by default.
CoreOobeHandler::CoreOobeHandler(OobeUI* oobe_ui)
    : oobe_ui_(oobe_ui),
      show_oobe_ui_(false) {
}

CoreOobeHandler::~CoreOobeHandler() {
}

void CoreOobeHandler::GetLocalizedStrings(
    base::DictionaryValue* localized_strings) {
  localized_strings->SetString(
      "productName", l10n_util::GetStringUTF16(IDS_SHORT_PRODUCT_NAME));
}

void CoreOobeHandler::Initialize() {
  UpdateOobeUIVisibility();
}

void CoreOobeHandler::RegisterMessages() {
  web_ui_->RegisterMessageCallback(kJsApiToggleAccessibility,
      NewCallback(this, &CoreOobeHandler::OnToggleAccessibility));
  web_ui_->RegisterMessageCallback(kJsApiScreenStateInitialize,
      NewCallback(this, &CoreOobeHandler::OnInitialized));
}

void CoreOobeHandler::OnInitialized(const ListValue* args) {
  oobe_ui_->InitializeHandlers();
}

void CoreOobeHandler::OnToggleAccessibility(const ListValue* args) {
  accessibility::ToggleAccessibility();
}

void CoreOobeHandler::ShowOobeUI(bool show) {
  if (show == show_oobe_ui_)
    return;

  show_oobe_ui_ = show;

  if (page_is_ready())
    UpdateOobeUIVisibility();
}

void CoreOobeHandler::UpdateOobeUIVisibility() {
  base::FundamentalValue showValue(show_oobe_ui_);
  web_ui_->CallJavascriptFunction("cr.ui.Oobe.showOobeUI", showValue);
}

// OobeUI ----------------------------------------------------------------------

OobeUI::OobeUI(TabContents* contents)
    : ChromeWebUI(contents),
      update_screen_actor_(NULL),
      network_screen_actor_(NULL),
      eula_screen_actor_(NULL),
      signin_screen_handler_(NULL) {
  core_handler_ = new CoreOobeHandler(this);
  AddScreenHandler(core_handler_);

  NetworkScreenHandler* network_screen_handler = new NetworkScreenHandler;
  network_screen_actor_ = network_screen_handler;
  AddScreenHandler(network_screen_handler);

  EulaScreenHandler* eula_screen_handler = new EulaScreenHandler;
  eula_screen_actor_ = eula_screen_handler;
  AddScreenHandler(eula_screen_handler);

  UpdateScreenHandler* update_screen_handler = new UpdateScreenHandler;
  update_screen_actor_ = update_screen_handler;
  AddScreenHandler(update_screen_handler);

  EnterpriseEnrollmentScreenHandler* enterprise_enrollment_screen_handler =
      new EnterpriseEnrollmentScreenHandler;
  enterprise_enrollment_screen_actor_ = enterprise_enrollment_screen_handler;
  AddScreenHandler(enterprise_enrollment_screen_handler);

  signin_screen_handler_ = new SigninScreenHandler;
  AddScreenHandler(signin_screen_handler_);

  DictionaryValue* localized_strings = new DictionaryValue;
  GetLocalizedStrings(localized_strings);

  // Set up the chrome://theme/ source, for Chrome logo.
  ThemeSource* theme = new ThemeSource(contents->profile());
  contents->profile()->GetChromeURLDataManager()->AddDataSource(theme);

  // Set up the chrome://terms/ data source, for EULA content.
  InitializeAboutDataSource(chrome::kChromeUITermsHost, contents->profile());

  // Set up the chrome://oobe/ source.
  OobeUIHTMLSource* html_source =
      new OobeUIHTMLSource(localized_strings);
  contents->profile()->GetChromeURLDataManager()->AddDataSource(html_source);

  // Set up the chrome://userimage/ source.
  UserImageSource* user_image_source = new UserImageSource();
  contents->profile()->GetChromeURLDataManager()->AddDataSource(
      user_image_source);
}

void OobeUI::ShowScreen(WizardScreen* screen) {
  screen->Show();
}

void OobeUI::HideScreen(WizardScreen* screen) {
  screen->Hide();
}

UpdateScreenActor* OobeUI::GetUpdateScreenActor() {
  return update_screen_actor_;
}

NetworkScreenActor* OobeUI::GetNetworkScreenActor() {
  return network_screen_actor_;
}

EulaScreenActor* OobeUI::GetEulaScreenActor() {
  return eula_screen_actor_;
}

EnterpriseEnrollmentScreenActor* OobeUI::
    GetEnterpriseEnrollmentScreenActor() {
  return enterprise_enrollment_screen_actor_;
}

UserImageScreenActor* OobeUI::GetUserImageScreenActor() {
  NOTIMPLEMENTED();
  return NULL;
}

ViewScreenDelegate* OobeUI::GetRegistrationScreenActor() {
  NOTIMPLEMENTED();
  return NULL;
}

ViewScreenDelegate* OobeUI::GetHTMLPageScreenActor() {
  NOTIMPLEMENTED();
  return NULL;
}

void OobeUI::GetLocalizedStrings(base::DictionaryValue* localized_strings) {
  // Note, handlers_[0] is a GenericHandler used by the WebUI.
  for (size_t i = 1; i < handlers_.size(); ++i) {
    static_cast<BaseScreenHandler*>(handlers_[i])->
        GetLocalizedStrings(localized_strings);
  }
  ChromeURLDataManager::DataSource::SetFontAndTextDirection(localized_strings);
}

void OobeUI::AddScreenHandler(BaseScreenHandler* handler) {
  AddMessageHandler(handler->Attach(this));
}

void OobeUI::InitializeHandlers() {
  // Note, handlers_[0] is a GenericHandler used by the WebUI.
  for (size_t i = 1; i < handlers_.size(); ++i) {
    static_cast<BaseScreenHandler*>(handlers_[i])->InitializeBase();
  }
}

void OobeUI::ShowOobeUI(bool show) {
  core_handler_->ShowOobeUI(show);
}

void OobeUI::ShowSigninScreen() {
  signin_screen_handler_->Show(core_handler_->show_oobe_ui());
}

}  // namespace chromeos
