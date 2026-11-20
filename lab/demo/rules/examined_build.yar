rule Authenticator_Downloader_Examined_Build {
  meta:
    scope = "Examined build, raw DEX only"
  strings:
    $service = "Lorg/hamcrest/UpdateService;" ascii
    $provider = "com.privacy.account.safetyapp.provider" ascii
    $install = "android.intent.action.INSTALL_PACKAGE" ascii
  condition:
    uint32(0) == 0x0a786564 and all of them
}
