// Observation only. Prints every network address the sample tries to reach.
Java.perform(() => {
  const Socket = Java.use('java.net.Socket');
  Socket.$init.overload('java.lang.String', 'int').implementation = function (host, port) {
    console.log('SOCKET=' + host + ':' + port);
    return this.$init(host, port);
  };
  const Address = Java.use('java.net.InetSocketAddress');
  Address.$init.overload('java.lang.String', 'int').implementation = function (host, port) {
    console.log('ADDRESS=' + host + ':' + port);
    return this.$init(host, port);
  };
  const Inet = Java.use('java.net.InetAddress');
  Inet.getByName.implementation = function (host) {
    console.log('RESOLVE=' + host);
    return this.getByName(host);
  };
  const URL = Java.use('java.net.URL');
  URL.openConnection.overload().implementation = function () {
    console.log('HTTP=' + this.toString());
    return this.openConnection();
  };
});
