"use client";

import { Collapsible } from "./Collapsible";

export function FormulaDetails() {
  return (
    <Collapsible
      title="Formula details"
      subtitle="How each number is built"
    >
      <div className="space-y-4">
        <p>
          Every scenario runs a Monte Carlo of the job. Tooling time, debug
          time, engineering hours, parts cost, yield, and downtime are all drawn
          from distributions, so each run produces a different cost to serve the
          job. That spread is what the charts show.
        </p>
        <div>
          <p className="font-semibold text-ink-50">Economic floor</p>
          <p className="mt-1">
            The all-in cost of one run: direct cost plus opportunity cost. Direct
            cost is line hours, engineering, and tooling parts. Opportunity cost
            is the value of the capacity you take off the market while the job
            runs.
          </p>
        </div>
        <div>
          <p className="font-semibold text-ink-50">Three multipliers</p>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            <li>
              Scarcity scales opportunity cost by how busy the factory is. Below
              60 percent it is 0.85. It climbs to 1.25 past 80 percent and 2.25
              above 97 percent.
            </li>
            <li>
              Parallelism prices concentration. A job that reserves a quarter of
              the lines or less is 1.00. Reserving the whole factory is 1.75,
              because taking every line at once is far more disruptive than one
              line for four times as long.
            </li>
            <li>
              Retooling scales tooling parts cost by complexity, from low to
              extreme.
            </li>
          </ul>
        </div>
        <div>
          <p className="font-semibold text-ink-50">From floor to quote</p>
          <p className="mt-1 font-mono text-[0.85rem] text-ink-100">
            target quote = risk floor / (1 - target margin)
          </p>
          <p className="mt-1">
            The risk floor is the economic floor at your chosen risk percentile,
            not the average, so the quote covers a bad run rather than a typical
            one. The expedited quote adds a premium on top:
          </p>
          <p className="mt-1 font-mono text-[0.85rem] text-ink-100">
            expedited quote = target quote x (1 + expedite willingness x parallelism)
          </p>
        </div>
      </div>
    </Collapsible>
  );
}

export function HowToRead() {
  return (
    <Collapsible title="How to read this" subtitle="Where to look and why">
      <div className="space-y-4">
        <p>
          Start with the metric cards. The target quote is what you should ask
          for to hit your margin. The expedited quote is what a rush job is
          worth once you account for how much of the factory it locks up.
        </p>
        <p>
          The comparison table lines up all three scenarios. They consume the
          same total line-weeks, so if pricing were only about hours they would
          cost the same. They do not. Watch the parallelism multiplier climb as
          the job compresses from one line for four weeks to four lines for one
          week. That is the whole point: 4 by 1 is not the same as 1 by 4.
        </p>
        <p>
          The floor chart shows the range of costs to serve the job. A wide
          spread means more uncertainty, which is why the quote is set at a risk
          percentile rather than the average. The margin chart shows what you
          actually keep if you win at the target quote. If a lot of that mass
          sits near or below break-even, the job is riskier than the headline
          number suggests.
        </p>
        <p>
          Use the controls to test your own case. Raise utilization to see
          scarcity bite, or drop the target margin to see the quote fall. The
          explanation panel restates, in words, why the selected scenario landed
          where it did.
        </p>
      </div>
    </Collapsible>
  );
}
