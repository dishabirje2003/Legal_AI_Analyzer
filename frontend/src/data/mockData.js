/** @typedef {'processing' | 'completed' | 'failed'} DocStatus */

/**
 * @typedef {Object} Document
 * @property {string} id
 * @property {string} name
 * @property {string} type
 * @property {string} uploadDate
 * @property {DocStatus} status
 * @property {number} pages
 * @property {string} size
 */

/** @type {Document[]} */
export const mockDocuments = [
  {
    id: '1',
    name: 'Property Purchase Agreement - 123 Main St',
    type: 'Property Agreement',
    uploadDate: '2026-03-20',
    status: 'completed',
    pages: 24,
    size: '2.4 MB',
  },
  {
    id: '2',
    name: 'Employment Contract - John Doe',
    type: 'Employment Contract',
    uploadDate: '2026-03-19',
    status: 'completed',
    pages: 12,
    size: '1.2 MB',
  },
  {
    id: '3',
    name: 'Rental Agreement - Downtown Office',
    type: 'Rental Contract',
    uploadDate: '2026-03-18',
    status: 'processing',
    pages: 15,
    size: '1.8 MB',
  },
  {
    id: '4',
    name: 'Court Judgment - Case #2026-CV-1234',
    type: 'Court Judgment',
    uploadDate: '2026-03-17',
    status: 'completed',
    pages: 32,
    size: '3.1 MB',
  },
];

/** Placeholder risk count for dashboard stats (AI analysis comes later) */
export const mockRiskCount = 4;

export const mockDocumentText = `PROPERTY PURCHASE AGREEMENT

This Agreement is entered into as of March 15, 2026, between:

BUYER: ABC Corporation
123 Business Plaza, Suite 400
Los Angeles, CA 90001

SELLER: XYZ Legal LLC
456 Commerce Street
San Francisco, CA 94102

WHEREAS, Seller is the lawful owner of the property located at 123 Main Street, Downtown District, and desires to sell the property to Buyer;

WHEREAS, Buyer desires to purchase the property from Seller;

NOW, THEREFORE, in consideration of the mutual covenants and agreements contained herein, the parties agree as follows:

1. PURCHASE PRICE AND PAYMENT
The purchase price for the property shall be Two Hundred Fifty Thousand Dollars ($250,000), payable as follows:
- Down payment: $50,000 upon signing
- Monthly installments: $5,000 per month
- Final balloon payment: $150,000 on December 31, 2027

2. PROPERTY DESCRIPTION
The property is described as follows:
Address: 123 Main Street, Downtown District
Parcel Number: 1234-567-890
Total Area: 2,500 square feet

3. PAYMENT TERMS
Buyer shall pay a monthly maintenance fee of Five Thousand Dollars ($5,000) beginning on the first day of each month.

Late payments shall incur a penalty of 15% of the outstanding amount per month.

4. REPRESENTATIONS AND WARRANTIES
Seller represents and warrants that:
- They have good and marketable title to the property
- The property is free from all liens and encumbrances
- All property taxes have been paid through the current date

5. CONFIDENTIALITY
Both parties agree to maintain confidentiality of all terms and conditions of this agreement.

6. TERMINATION
Either party may terminate this agreement with 30 days written notice to the other party.

7. GOVERNING LAW
This Agreement shall be governed by and construed in accordance with the laws of the State of California.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

_______________________
ABC Corporation
By: Jane Smith, CEO

_______________________
XYZ Legal LLC
By: Robert Johnson, Managing Partner`;

/** @param {string} id */
export function getDocumentById(id) {
  return mockDocuments.find((d) => d.id === id) ?? null;
}
