import glob
import logging
import os
import random
import sys

from mock import Mock
sys.modules["PyQt5"] = Mock()
sys.modules["PyQt5.QtWidgets"] = Mock()
sys.modules["PyQt5.QtCore"] = Mock()

import Configuration
import Importer

try:
    from bulkimport_config import *
except ImportError:
    print "Please create bulkimport_config.py (you can use bulkimport_config_sample.py)"
    import sys
    sys.exit(1)

settings = {}
if os.name == 'nt':
    settings['os'] = 'windows'
else:
    settings['os'] = 'linuxmac'

log = logging.getLogger("importer")

Configuration.set_logfile(IMPORT_LOG_FILE)
config = Configuration.Config()

file_names = glob.glob(os.path.join(IMPORT_PATH, IMPORT_FILE_PATTERN))
file_names.sort(cmp=lambda x, y: random.randint(-1, 1))
file_names = file_names[:IMPORT_NUM_OF_FILES]

if file_names:
    importer = Importer.Importer(False, settings, config, None)

    for file_name in file_names:
        log.info("importing %s..." % file_name)
        importer.addImportFile(os.path.expanduser(file_name))

    importer.setCallHud(False)
    (stored, dups, partial, skipped, errors, runtime) = importer.runImport()
    importer.clearFileList()
    log.info("Import done")
    log.info("Stored: %d   Dupl: %d   Partial: %d   Skipped: %d   Err: %d   HH/sec: %.0f  " %
             (stored, dups, partial, errors, skipped, (stored + 0.0) / runtime))
