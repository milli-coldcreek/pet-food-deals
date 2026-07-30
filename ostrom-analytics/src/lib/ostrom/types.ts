export type Environment = "production" | "sandbox";

export type Resolution = "HOUR" | "DAY" | "MONTH";

export interface OstromCredentials {
  clientId: string;
  clientSecret: string;
  environment: Environment;
}

export interface ContractAddress {
  zip: string;
  city: string;
  street: string;
  houseNumber: string;
}

export interface Contract {
  id: number;
  type: string;
  productCode: string;
  status: string;
  customerFirstName: string;
  customerLastName: string;
  startDate: string;
  currentMonthlyDepositAmount: number | string;
  address: ContractAddress;
}

export interface ConsumptionPoint {
  date: string;
  kWh: number;
}

export interface SpotPricePoint {
  date: string;
  netMwhPrice: number;
  netKwhPrice: number;
  grossKwhPrice: number;
  netKwhTaxAndLevies: number;
  grossKwhTaxAndLevies: number;
  netMonthlyOstromBaseFee: number;
  grossMonthlyOstromBaseFee: number;
  netMonthlyGridFees: number;
  grossMonthlyGridFees: number;
}

export interface EnrichedPoint {
  date: string;
  timestamp: number;
  kWh: number;
  /** Gross ct/kWh including taxes & levies */
  priceCt: number | null;
  /** Estimated cost in EUR for this interval */
  costEur: number | null;
}

export interface SessionConfig {
  mode: "live" | "demo";
  clientId?: string;
  clientSecret?: string;
  environment?: Environment;
  contractId?: number;
  zip?: string;
}
