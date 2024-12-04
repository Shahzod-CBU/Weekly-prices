# Weekly-prices
Online Price Input and Monitoring App for Central Bank

CBU has 14 regional branches and every week they conduct price monitoring in markets. 
To automate the process of data collection I created this site which is easy-to-use for both data collectors (regions) and data-engineers (headquarter).

### Examples of the interface
#### Login page
![example1](site1.png)

#### Data inputting page for regions
![example2](site2.png)

#### Data checking page
![example3](site3.png)

#### Django admin page
![example4](site4.png)

## Key Features:
- **Price Input System:**
  - Easy-to-use web interface for regional branches to input weekly market prices.
  - Data validation and real-time saving for seamless operation.

- **Automated Data Processing:**
  - Aggregates data from regional markets and supermarkets.
  - Computes weighted averages based on regional population and market weights.
  - Supports pivot tables and advanced calculations for analysis.

- **Change Monitoring:**
  - Provides detailed insights into price changes across regions and categories (food, non-food, services).
  - Highlights discrepancies in data collection.

- **Reports and Exports:**
  - Generates Excel reports for price trends, changes, and regional breakdowns.
  - Allows data engineers to export data for further analysis.

- **Admin Controls:**
  - Role-based access with separate views for staff and regular users.
  - Bulk import functionality for goods, prices, and market weights via Excel files.
  - Customizable date management for weekly data collection.

## Workflow:
1. **Data Input:**
   - Regional branches input prices via the web interface.
   - Data is validated and stored in the database.

2. **Data Aggregation:**
   - Headquarters access aggregated data for analysis and reporting.
   - Advanced tools compute weighted averages and price indices.

3. **Monitoring and Reporting:**
   - Staff members monitor changes, generate reports, and export results for further processing.

## Technology Stack:
- **Backend:** 
  - Django framework for server-side logic.
  - MySQL/PostgreSQL for data storage.

- **Frontend:**
  - HTML, CSS, JavaScript for user interfaces.
  - Bootstrap and Django templates for responsive design.

- **Data Processing:**
  - Pandas and NumPy for data manipulation and analysis.
  - Scipy for advanced statistical calculations.

## Usage:
1. Set up the application with Django and configure database settings.
2. Deploy the app for use by regional branches and headquarters.
3. Use the admin panel to manage users, data, and reports.

## Example Use Cases:
- Weekly market price monitoring across regions.
- Inflation trend analysis based on collected prices.
- Automating manual processes for data collection and reporting.

This web application empowers the Central Bank to streamline its price monitoring process, ensuring accuracy, efficiency, and transparency in data collection and analysis. 
