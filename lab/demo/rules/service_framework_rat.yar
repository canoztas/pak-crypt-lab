rule Service_Framework_RAT {
  meta:
    scope = "Examined build, raw DEX only"
  strings:
    $server = "3.67.78.149" ascii
    $config = "Lcom/example/reverseshell2/config;" ascii
    $client = "Lcom/example/reverseshell2/tcpConnection;" ascii
    $audio = "Lcom/example/reverseshell2/Payloads/audioManager;" ascii
    $banner = "Hello there, welcome to reverse shell of " ascii
  condition:
    uint32(0) == 0x0a786564 and 4 of them
}
