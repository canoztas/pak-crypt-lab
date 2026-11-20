// Observation only. Prints every file the app writes or renames while it runs.
Java.perform(() => {
  const FOS = Java.use('java.io.FileOutputStream');
  FOS.$init.overload('java.io.File', 'boolean').implementation = function (file, append) {
    console.log('WRITE=' + file.getAbsolutePath());
    return this.$init(file, append);
  };
  const File = Java.use('java.io.File');
  File.renameTo.implementation = function (destination) {
    console.log('RENAME=' + this.getAbsolutePath() + ' -> ' + destination.getAbsolutePath());
    return this.renameTo(destination);
  };
});
