# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


class ExponentialMovingAverage:
    def __init__(self, alpha):
        self.alpha = alpha
        self.state = 0

    def __call__(self, input_):
        alpha = self.alpha
        self.state = output = alpha * input_ + (1 - alpha) * self.state
        
        return output
