# Copyright 2015 Carnegie Mellon University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module for Torch-based neural network usage."""

import atexit
import binascii
from subprocess import Popen, PIPE
import os
import os.path
import sys

import numpy as np
import cv2

myDir = os.path.dirname(os.path.realpath(__file__))

# Workaround for non-standard terminals, originally reported in
# https://github.com/cmusatyalab/openface/issues/66
os.environ['TERM'] = 'linux'


class TorchNeuralNet:
    """Use a `Torch <http://torch.ch>`_ subprocess for feature extraction."""

    #: The default Torch model to use.
    defaultModel = os.path.join(myDir, '..', 'models', 'openface', 'nn4.v1.t7')

    def __init__(self, model=defaultModel, imgDim=96, cuda=False):
        """__init__(self, model=defaultModel, imgDim=96, cuda=False)

        Instantiate a 'TorchNeuralNet' object.

        Starts `openface_server.lua
        <https://github.com/cmusatyalab/openface/blob/master/openface/openface_server.lua>`_
        as a subprocess.

        :param model: The path to the Torch model to use.
        :type model: str
        :param imgDim: The edge length of the square input image.
        :type imgDim: int
        :param cuda: Flag to use CUDA in the subprocess.
        :type cuda: bool
        """
        self.cmd = ['/usr/bin/env', 'th', os.path.join(myDir, 'openface_server.lua'),
                    '-model', model, '-imgDim', str(imgDim)]
        if cuda:
            self.cmd.append('-cuda')
        self.p = Popen(self.cmd, stdin=PIPE, stdout=PIPE,
                       stderr=PIPE, bufsize=0)

        def exitHandler():
            if self.p.poll() is None:
                self.p.kill()
        atexit.register(exitHandler)

    def forwardPath(self, imgPath):
        """
        Perform a forward network pass of an image on disk.

        :param imgPath: The path to the image.
        :type imgPath: str
        :return: Vector of features extracted with the neural network.
        :rtype: numpy.ndarray
        """
        rc = self.p.poll()
        if rc is not None and rc != 0:
            raise Exception("""


OpenFace: `openface_server.lua` subprocess has died.
Is the Torch command `th` on your PATH? Check with `which th`.

Diagnostic information:

cmd: {}

============

stdout: {}

============

stderr: {}
""".format(self.cmd, self.p.stdout.read(), self.p.stderr.read()))

        self.p.stdin.write(imgPath + "\n")
        output = self.p.stdout.readline()
        try:
            rep = [float(x) for x in output.strip().split(',')]
            rep = np.array(rep)
            return rep
        except Exception as e:
            self.p.kill()
            stdout, stderr = self.p.communicate()
            print("""


Error getting result from Torch subprocess.

Line read: {}

Exception:

{}

============

stdout: {}

============

stderr: {}
""".format(output, str(e), stdout, stderr))
            sys.exit(-1)

    def forward(self, rgbImg):
        """
        Perform a forward network pass of an RGB image.

        :param rgbImg: RGB image to process. Shape: (imgDim, imgDim, 3)
        :type rgbImg: numpy.ndarray
        :return: Vector of features extracted from the neural network.
        :rtype: numpy.ndarray
        """
        if rgbImg is None:
            raise Exception("rgbImg=None passed into forward")
        t = '/tmp/openface-torchwrap-{}.png'.format(
            binascii.b2a_hex(os.urandom(8)))
        bgrImg = cv2.cvtColor(rgbImg, cv2.COLOR_RGB2BGR)
        cv2.imwrite(t, bgrImg)
        rep = self.forwardPath(t)
        os.remove(t)
        return rep
