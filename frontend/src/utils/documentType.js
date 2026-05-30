  
export function formatDocumentType(value) {  
  const key = String(value ?? '').toLowerCase();  
  if (['contract', 'property_agreement', 'rental_contract', 'employment_contract'].includes(key)) return 'Contracts';  
  if (key === 'court_judgment') return 'Court Judgment';  
  if (key === 'general_legal_document') return 'General Legal Document';  
  return value ?? 'Legal Document';  
}  
  
export function formatContractSubtype(value) {  
  const key = String(value ?? '').toLowerCase();  
  if (key === 'rental_contract') return 'Rental Contract';  
  if (key === 'employment_contract') return 'Employment Contract';  
  if (key === 'property_agreement') return 'Property Agreement';  
  return '';  
}  
  
export function typeMatchesFilter(value, filter) {  
  if (filter === 'all') return true;  
  const key = String(value ?? '').toLowerCase();  
  if (filter === 'contract') return ['contract', 'property_agreement', 'rental_contract', 'employment_contract'].includes(key);  
  return key === filter;  
}  
