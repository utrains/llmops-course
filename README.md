# LLMOps Course

Welcome to the LLMOps Course.

This repository is organized by week. Each week has its own dedicated folder for the lab materials, and each lab folder includes a README with the instructions you need to follow the lab step by step.

The labs materials are the following:

- Week 1: [week01](./week01/README.md)
- Week 2: [week02](./week02/README.md)
- Week 3: coming soon
- Week 4: coming soon
- Week 5: coming soon
- Week 6: coming soon
- Week 7: coming soon
- Week 8: coming soon

## The arc

Each week answers one question. It is worth knowing which one you are on.

| | The question the week answers |
|---|---|
| Week 1 | Can I get an answer at all, and what did I give up to get it? |
| Week 2 | Can I trust that answer enough to hand it to another system? |
| Weeks 3 and 4 | Can I make it answer about *my* data? |
| Week 5 | Can I let it take actions? |
| Weeks 6 to 8 | Can I run it, watch it, and roll it back? |

Two boundaries run through the whole course.

**Week 1 is the boundary between your company and the model.** Local or hosted, which model, whose
datacentre, whose terms of service. Cost per token, latency, data sovereignty and vendor lock-in all
follow from that one decision.

**Week 2 onwards is the boundary between the model and the rest of your software.** The consumer of
a model's output is usually not a human. A person reads a paragraph and fills in the gaps. A
microservice cannot. Most of this course is about making that output safe to pass across that
boundary.

Three things make this harder than the software you have run before:

- **Failure is silent.** A wrong answer does not raise. No stack trace, no 500, no alert. Your
  dashboards stay green while the model tells a customer something false.
- **The same input can produce a different output**, today and again next month when the provider
  updates the model underneath you.
- **Quality has to be measured, not felt.** That is the *Ops* in LLMOps.

Get this wrong and it is not just an awkward answer. It is your company's reputation, and it is bad
data travelling on into every service downstream that trusted yours.
