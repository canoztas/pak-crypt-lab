// Observation only. Logs the sample's own AES key and what it decrypts; nothing is sent anywhere.
Java.perform(() => {
  const S = Java.use('java.lang.String');
  const SecretKeySpec = Java.use('javax.crypto.spec.SecretKeySpec');
  SecretKeySpec.$init.overload('[B', 'java.lang.String').implementation = function (key, algorithm) {
    console.log('KEY ' + algorithm + '=' + S.$new(key));
    return this.$init(key, algorithm);
  };
  const Cipher = Java.use('javax.crypto.Cipher');
  Cipher.doFinal.overload('[B').implementation = function (input) {
    const output = this.doFinal(input);
    if (output.length < 200) {
      console.log('PLAINTEXT=' + S.$new(output));
    } else {
      const head = [];
      for (let i = 0; i < 4; i++) head.push((output[i] & 0xff).toString(16));
      console.log('BLOB=' + output.length + ' bytes, first bytes ' + head.join(' '));
    }
    return output;
  };
});
