# SPDX-License-Identifier: Apache-2.0
# Keep the rest of the vendor file byte-for-byte unchanged.
# Inline the controls: audio_route resolves nested paths in declaration order.
$0 == "    <path name=\"handset-mic\">" {
    if (++found != 1) {
        exit 1
    }
    print "    <!-- Use the working speakerphone input ordering; inline to avoid forward path references. -->"
    print
    print "        <ctl name=\"MI2S_TX Channels\" value=\"Two\" />"
    print "        <ctl name=\"ADC3 Volume\" value=\"6\" />"
    print "        <ctl name=\"DEC1 MUX\" value=\"ADC2\" />"
    print "        <ctl name=\"ADC2 MUX\" value=\"INP3\" />"
    print "        <ctl name=\"ADC1 Volume\" value=\"6\" />"
    print "        <ctl name=\"DEC2 MUX\" value=\"ADC1\" />"
    skipping = 1
    next
}
skipping {
    if ($0 == "    </path>") {
        skipping = 0
        print
    }
    next
}
{ print }
END {
    if (found != 1 || skipping) {
        exit 1
    }
}
