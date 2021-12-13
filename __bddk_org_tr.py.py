import time
import json
from bddk_org_tr import *

if __name__ == '__main__':
    start_time = time.time()

    a = Handler()

    final_data = a.Execute('ARMADA', '', '', '')
    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print('\nTask completed - Elapsed time: ' + str(round(elapsed_time, 2)) + ' seconds')
