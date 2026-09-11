const fs = require('fs');

// This creates a small, readable handbook PDF for the lab repository.
// The notebook still teaches the production pattern: a PDF loader reads pages,
// a splitter creates chunks, and the vector store indexes those chunks.
const sections = [
  ['Company Handbook', 'This handbook describes the policies used by the company.'],
  ['Time Off', 'Full-time employees receive 20 vacation days each calendar year. Requests should be submitted through the employee portal.'],
  ['Parental Leave', 'Eligible employees may receive 20 weeks of paid parental leave. The leave team confirms eligibility before approval.'],
  ['Travel and Expenses', 'Employees may book standard rail travel without approval when the cost is below USD 250 per trip. Receipts are required.'],
  ['Medical Benefits', 'Employees can select individual or family coverage during the enrollment window. The benefits team publishes current plan costs.'],
  ['Onboarding', 'New employees complete security training, identity verification, and equipment setup during their first week.'],
  ['Remote Work', 'Remote work requires an approved work location and compliance with the company security policy.'],
  ['Questions and Exceptions', 'Ask the HR operations team when a policy is unclear. Approved exceptions must be recorded in the HR system.']
];

// Repeat realistic handbook sections so the lab works with a longer document.
// A production corpus would contain many separate source documents instead.
while (sections.length < 40) {
  const number = sections.length + 1;
  sections.push([
    `Operations Policy ${number}`,
    `This handbook section describes an approved company process, its owner, the required records, and the exception path. Employees should follow the current version published by the policy owner.`
  ]);
}

const objects = [];
objects[1] = '<< /Type /Catalog /Pages 2 0 R >>';
objects[2] = '<< /Type /Pages /Kids [' + sections.map((_, i) => `${5 + i * 2} 0 R`).join(' ') + `] /Count ${sections.length} >>`;
objects[4] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>';

for (let i = 0; i < sections.length; i++) {
  const pageObject = 5 + i * 2;
  const contentObject = pageObject + 1;
  const [title, body] = sections[i];
  const lines = [title, body, `Handbook section ${i + 1}`, 'Source: company_handbook.pdf'];
  const commands = ['BT', '/F1 18 Tf', '72 720 Td'];
  for (const line of lines) {
    const safe = line.replaceAll('\\', '\\\\').replaceAll('(', '\\(').replaceAll(')', '\\)');
    commands.push(`(${safe}) Tj`, '0 -28 Td', '/F1 11 Tf');
  }
  commands.push('ET');
  const stream = commands.join('\n');
  objects[pageObject] = `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents ${contentObject} 0 R >>`;
  objects[contentObject] = `<< /Length ${Buffer.byteLength(stream, 'latin1')} >>\nstream\n${stream}\nendstream`;
}

let pdf = '%PDF-1.4\n';
const offsets = [0];
for (let i = 1; i < objects.length; i++) {
  offsets[i] = Buffer.byteLength(pdf, 'latin1');
  pdf += `${i} 0 obj\n${objects[i]}\nendobj\n`;
}
const xref = Buffer.byteLength(pdf, 'latin1');
pdf += `xref\n0 ${objects.length}\n0000000000 65535 f \n`;
for (let i = 1; i < objects.length; i++) pdf += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
pdf += `trailer\n<< /Size ${objects.length} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
fs.writeFileSync('sample_documents/company_handbook.pdf', pdf, 'latin1');
