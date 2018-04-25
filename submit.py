#!/usr/bin/env python

from itertools import count
import os
import pipes
import re
import subprocess
from helperstuff.submitjob import submitjob

import constants

here = os.path.abspath(os.path.dirname(__file__))

class Sample(object):
  def __init__(self, productionmode, hypothesis, index=1):
    self.productionmode = productionmode
    self.hypothesis = hypothesis
    self.index = index

  def commandline(self, dryrun=False):
    result = [os.path.join(here, "..", "JHUGen")]
    result += ["Unweighted=0", "VegasNc0=99999999", "VegasNc1=99999999", "VegasNc2=99999999", "PDFSet=3", "DataFile=workdir/"+self.jobname, "MPhotonCutoff=0"]
    if dryrun:
      result += ["DryRun"]

    if self.productionmode == "HZZ":
      result += ["Interf=0"]
    elif self.productionmode == "HWW":
      result += ["DecayMode1=11", "DecayMode2=11"]
    elif self.productionmode == "VBF":
      result += ["Process=60", "deltaRcut=0"]
      if self.hypothesis == "L1Zg":
        result += ["pTjetcut=15"]
      else:
        result += ["pTjetcut=0"]
    elif self.productionmode == "ZH":
      result += ["Process=50", "DecayMode1=9"]
    elif self.productionmode == "WH":
      result += ["Process=50", "DecayMode1=11"]
    else:
      assert False

    result += self.couplings

    return result

  @staticmethod
  def JHUGencoupling(coupling):
    if coupling == "a1": return "ghz1"
    if coupling == "a2": return "ghz2"
    if coupling == "a3": return "ghz4"
    if coupling == "L1": return "ghz1_prime2"
    if coupling == "L1Zg": return "ghzgs1_prime2"
    assert False, coupling
  @staticmethod
  def constantscoupling(coupling):
    if coupling == "a1": return "g1"
    if coupling == "a2": return "g2"
    if coupling == "a3": return "g4"
    if coupling == "L1": return "g1prime2"
    if coupling == "L1Zg": return "ghzgs1prime2"
    assert False, coupling

  def couplingvalue(self, coupling):
    if coupling == "a1": return 1
    return getattr(constants, self.constantscoupling(coupling)+self.productionmode)

  @property
  def couplings(self):
    if self.hypothesis == "a1":
      return ["ghz1=1,0"]
    if self.hypothesis == "a2":
      return ["ghz1=0,0", "ghz2=1,0"]
    if self.hypothesis == "a3":
      return ["ghz1=0,0", "ghz4=1,0"]
    if self.hypothesis == "L1":
      return ["ghz1=0,0", "ghz1_prime2=1,0"]
    if self.hypothesis == "L1Zg":
      return ["ghz1=0,0", "ghzgs1_prime2=1,0"]

    match = re.match("(a1|a2|a3|L1|L1Zg)(a1|a2|a3|L1|L1Zg)$", self.hypothesis)
    assert match
    result = []
    if "a1" not in self.hypothesis: result.append("ghz1=0,0")
    for g in range(1, 3):
      coupling = match.group(g)
      result.append("{}={},0".format(self.JHUGencoupling(coupling), self.couplingvalue(coupling)))
    return result

  def dryrun(self):
    subprocess.check_call(self.commandline(dryrun=True))

  @property
  def jobname(self):
    return (self.productionmode + "_" + self.hypothesis
         + ("_{}".format(self.index) if self.index > 1 else ""))

  @property
  def outputfile(self):
    return os.path.join(here, self.jobname+".out")

  def submit(self):
    if os.path.exists(self.outputfile): return
    self.dryrun()
    print self.jobname
    link = [":", "ln", "-s", os.path.join(here, "..", "pdfs")]
    export = ["export", "LD_LIBRARY_PATH=/work-zfs/lhc/heshy/JHUGen/xsecs/JHUGen_interference/JHUGenMELA/MELA/data/slc6_amd64_gcc530:"+os.environ["LD_LIBRARY_PATH"]]
    commands = [link, export, self.commandline()]
    jobtext = " && ".join(" ".join(pipes.quote(_) for _ in command) for command in commands)
    print jobtext
    submitjob(
      jobtext = jobtext,
      jobname = self.jobname,
      jobtime = "2-0:0:0" if self.productionmode in "HZZ HWW" else "1-0:0:0",
      outputfile = self.outputfile,
      email = True,
      docd=True,
    )

  @property
  def xsec(self):
    xsec = error = None
    with open(self.outputfile) as f:
      for line in f:
        match = re.match("# *integral *= *[0-9.Ee+-Na]* *accum. integral *= *([0-9.Ee+-Na]*) *[*]", line.strip())
        if match:
          result = float(match.group(1))
          xsec = result
        match = re.match("# *std. dev. *= *[0-9.Ee+-Na]* *accum. std. dev *= *([0-9.Ee+-Na]*) *[*]", line.strip())
        if match:
          result = float(match.group(1))
          error = result
        if line.strip() == "Done": return xsec, error
    return None, None


def main(whattodo, ufloat):
  kwargs = {}
  for kwargs["productionmode"] in "VBF", "ZH", "WH", "HZZ", "HWW":
    for kwargs["hypothesis"] in "a1", "a2", "a3", "L1", "L1Zg", "a1a2", "a1a3", "a1L1", "a1L1Zg", "a2a3", "a2L1", "a2L1Zg", "a3L1", "a3L1Zg", "L1L1Zg":
      if "L1Zg" in kwargs["hypothesis"] and kwargs["productionmode"] in ("WH", "HWW"): continue

      if whattodo == "submit":
        for kwargs["index"] in range(1, 20 if kwargs["productionmode"] in ("ZH", "WH") else 2):
          Sample(**kwargs).submit()

      elif whattodo == "calc":
        numerator = denominator = 0
        for kwargs["index"] in count(1):
          try:
            xsec, error = Sample(**kwargs).xsec
            if xsec is not None is not error and xsec == xsec and error == error:
              numerator += xsec/error**2
              denominator += 1/error**2
          except IOError:
            break
        if numerator == denominator == 0: numerator = denominator = float("nan")
        kwargs["index"] = 1
        fmt = "{:20} {:.6g} +/- {:.6g}" 
        name = Sample(**kwargs).jobname
        if ufloat:
          fmt = "{:26} = ufloat({:14.8g}, {:14.8g})"
          name = "JHUXS"+name.replace("_", "").replace("HZZ", "HZZ2L2l")
        print fmt.format(name, numerator/denominator, 1/denominator**.5)
      else:
        assert False

if __name__ == "__main__":
  import argparse
  p = argparse.ArgumentParser()
  p.add_argument("whattodo", choices=("submit", "calc"))
  p.add_argument("--ufloat", action="store_true")
  args = p.parse_args()
  main(args.whattodo, args.ufloat)
