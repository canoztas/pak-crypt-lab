// Read the static String fields of the downloader's constants class (h.c.e.a) at runtime.
// Observation only: reflection reads the fields; no method of the sample is called.
// The indicator domain is printed defanged.
Java.perform(() => {
  const C = Java.use('h.c.e.a');
  for (const f of C.class.getDeclaredFields()) {
    f.setAccessible(true);
    const v = f.get(null);
    if (v !== null) console.log('CONST=' + String(v).replace(/privacyandroidapp\.club/g, 'privacyandroidapp[.]club'));
  }
});
