# Fulfillment Hub

A Streamlit-based order fulfillment management prototype for tracking orders, inventory, exceptions, staging, and courier dispatch.

## 1. Project Overview

Fulfillment Hub is an order fulfillment management prototype designed for a small e-commerce operation.

The application provides a centralized workflow for managing orders from receipt through shipment, while improving visibility of inventory, order status, exceptions, staging, and courier handoff.

The main objective is to reduce operational delays, prevent fulfillment errors, and provide a structured process for handling operational exceptions.

---

## 2. Problem Statement

The existing fulfillment process relies heavily on spreadsheets and shared folders.

The major operational problems identified were:

- No centralized visibility of order status
- Priority orders may get mixed with regular orders
- Inventory information may not match physical stock
- Wrong product, variant, or quantity may be picked
- Packed orders may be misplaced
- Courier pickup issues may go unnoticed
- Operational problems may be handled informally
- No standardized exception tracking
- Delays may go unnoticed

---

## 3. Proposed Solution

Fulfillment Hub provides a centralized operational workflow where:

- Orders are tracked through defined statuses
- Priority and warehouse assignment are verified
- Physical inventory is checked before order confirmation
- Secondary warehouse stock can be transferred to Main when required
- Stock is reserved before fulfillment
- Picking and packing require verification
- Staging locations are tracked
- Courier handoff requires verification
- Shipment requires a tracking number
- Operational exceptions can be recorded and resolved
- Different users have controlled permissions based on their role

---

## 4. Order Fulfillment Flow

The complete order fulfillment process is:

```text
                    ┌─────────────────────┐
                    │   ORDER RECEIVED    │
                    └──────────┬──────────┘
                               │
                               ↓
                 ┌──────────────────────────┐
                 │ Verify Priority &        │
                 │ Assign Warehouse         │
                 └────────────┬─────────────┘
                              │
                              ↓
                 ┌──────────────────────────┐
                 │   Physical Stock Check   │
                 └────────────┬─────────────┘
                              │
                              ↓
                    ┌────────────────────┐
                    │ Sufficient Stock   │
                    │ in Main Warehouse? │
                    └───────┬──────┬─────┘
                            │      │
                          YES      NO
                            │      │
                            ↓      ↓
                  ┌────────────┐  ┌─────────────────────┐
                  │   Reserve  │  │ Check Secondary     │
                  │   Stock    │  │ Warehouse            │
                  └─────┬──────┘  └──────────┬──────────┘
                        │                    │
                        │                    ↓
                        │          ┌──────────────────┐
                        │          │ Stock Available  │
                        │          │ in Secondary?    │
                        │          └───────┬─────┬────┘
                        │                  │     │
                        │                YES     NO
                        │                  │     │
                        │                  ↓     ↓
                        │       ┌─────────────────┐
                        │       │ Warehouse        │
                        │       │ physically moves │
                        │       │ Secondary → Main │
                        │       └────────┬────────┘
                        │                │
                        │                ↓
                        │       ┌─────────────────┐
                        │       │ Recheck Main    │
                        │       │ Stock           │
                        │       └────────┬────────┘
                        │                │
                        │                ↓
                        │       ┌─────────────────┐
                        │       │  Reserve Stock  │
                        │       └────────┬────────┘
                        │                │
                        └────────┬───────┘
                                 │
                                 ↓
                       ┌─────────────────┐
                       │    CONFIRMED    │
                       └────────┬────────┘
                                │
                                ↓
                  ┌──────────────────────────┐
                  │ Courier Assignment &     │
                  │ Shipping Label           │
                  └────────────┬─────────────┘
                               │
                               ↓
                        ┌─────────────┐
                        │   PICKING   │
                        └──────┬──────┘
                               │
                               ↓
                      Pick Verification
                               │
                               ↓
                        ┌─────────────┐
                        │    PICKED   │
                        └──────┬──────┘
                               │
                               ↓
                     Packing Verification
                               │
                               ↓
                        ┌─────────────┐
                        │    PACKED   │
                        └──────┬──────┘
                               │
                               ↓
                       Send to Staging
                               │
                               ↓
                        ┌─────────────┐
                        │    STAGED   │
                        └──────┬──────┘
                               │
                               ↓
                    Assign Staging Location
                               │
                               ↓
                     ┌───────────────────┐
                     │ Ready for Pickup  │
                     └─────────┬─────────┘
                               │
                               ↓
                        Courier Handoff
                               │
                               ↓
                    ┌─────────────────────┐
                    │ Handed to Courier   │
                    └──────────┬──────────┘
                               │
                               ↓
                        Tracking Number
                               │
                               ↓
                         ┌──────────┐
                         │ SHIPPED  │
                         └──────────┘
```

---

## 5. Stock Shortage Handling

Orders are shipped from the Main warehouse.

If sufficient stock is not available in Main:

1. The system checks Secondary warehouse stock.
2. If sufficient stock exists in Secondary, the Warehouse team physically moves the required stock to Main.
3. The transfer is confirmed in the application after the physical movement.
4. Main warehouse stock is rechecked.
5. The order can then proceed to stock reservation and confirmation.

If sufficient stock is not available in either warehouse, an **Insufficient Stock Exception** is recorded and the order does not proceed to picking until the issue is handled.

### Stock Decision Flow

```text
Main Stock Available?
        │
       YES
        ↓
  Reserve Stock
        ↓
    Confirmed
        ↓
Continue Fulfillment
```

```text
Main Stock Available?
        │
       NO
        ↓
Check Secondary Warehouse
        ↓
   Stock Available?
      /       \
    YES        NO
     ↓          ↓
Transfer      Insufficient
Secondary     Stock Exception
→ Main
     ↓
Recheck Main Stock
     ↓
Reserve Stock
     ↓
Confirmed
     ↓
Continue Fulfillment
```

---

## 6. Inventory Logic

The application tracks:

- Physical Stock
- Reserved Stock
- Available Stock

The calculation is:

```text
Available Stock = Physical Stock - Reserved Stock
```

### When an order is confirmed

The required quantity is reserved.

```text
Physical Stock  → No change
Reserved Stock  → Increases
Available Stock → Decreases
```

### When an order is picked

The physical stock is consumed and the reservation is released.

```text
Physical Stock  → Decreases
Reserved Stock  → Decreases
Available Stock → Remains consistent
```

This prevents the same inventory from being deducted twice.

---

## 7. Order Statuses

The application tracks orders through defined operational statuses:

- Received
- Confirmed
- Picking
- Picked
- Packed
- Staged
- Ready for Pickup
- Handed to Courier
- Shipped

The status is updated whenever an order moves to the next operational stage.

---

## 8. Exception Management

The application provides structured exception management for operational problems.

Supported exception types include:

- Insufficient stock
- Stock not physically verified
- Wrong product / variant
- Wrong quantity
- Misplaced package
- Staging capacity
- Courier / pickup issue
- Picking stock mismatch
- Other operational issue

Each exception contains information such as:

- Order ID
- Exception type
- Description
- Owner
- Status
- Created time
- Resolution

Exceptions can be assigned to the appropriate operational owner and resolved by authorized Operations users.

---

## 9. Exception Flow

```text
             Operational Problem
                     ↓
              Create Exception
                     ↓
                Assign Owner
                     ↓
                 Investigate
                     ↓
              ┌──────────────┐
              │ Issue        │
              │ Resolved?    │
              └──────┬───────┘
                 YES │ NO
                     │
          ┌──────────┴──────────┐
          ↓                     ↓
   Record Resolution     Take Corrective
          │                  Action
          │                     │
          │                     ↓
          │               Investigate
          │                  Again
          │                     │
          └──────────┬──────────┘
                     ↓
             Mark as Resolved
```

---

## 10. Staging Management

The prototype contains 16 physical staging locations:

- A-01 to A-08
- B-01 to B-08

Staging locations are assigned to orders when they are moved to **Ready for Pickup**.

Orders currently in:

- Staged
- Ready for Pickup

are considered to occupy staging locations.

When an order is handed to the courier, its staging location becomes available for reuse.

If all staging locations are occupied, a **Staging Capacity Exception** can be recorded.

---

## 11. User Roles

### Admin / Operations Lead

Responsible for overall operational control.

Can manage and oversee:

- Order workflow
- Inventory
- Exceptions
- Stock transfers
- Dispatch activities

### Office / Operations

Responsible for:

- Priority verification
- Warehouse assignment
- Courier assignment
- Shipping label creation
- Order coordination
- Exception coordination and resolution

### Warehouse

Responsible for:

- Physical stock verification
- Picking
- Packing verification
- Staging
- Physical stock movement
- Inventory updates

### Dispatch

Responsible for:

- Courier verification
- Courier handoff
- Shipment confirmation

### Viewer

Can view operational information but cannot perform controlled operational actions.

---

## 12. Application Pages

### Dashboard

Provides an operational overview including:

- Total Orders
- High Priority Orders
- Open Exceptions
- Delayed Active Orders
- Ready for Pickup Orders
- Order Status Distribution

### Order Control

Used to manage individual orders through the fulfillment workflow.

### Inventory & Pick/Pack

Used for:

- Inventory visibility
- Physical stock verification
- Secondary → Main stock transfer
- Low stock monitoring
- Picking
- Packing verification

### Dispatch

Used for:

- Staging
- Staging location assignment
- Courier handoff
- Shipment confirmation

### Order History

Provides historical information about handed-over and shipped orders.

### Exceptions

Used to:

- Report operational exceptions
- View exceptions
- Assign ownership
- Record resolutions

---

## 13. Technology Used

- Python
- Streamlit
- Pandas
- Plotly
- CSV

The prototype uses CSV files for data storage to keep the solution simple and suitable for a small operational environment.

---

## 14. Project Structure

```text
Fulfillment-Hub/
│
├── app.py
├── requirements.txt
│
└── data/
    ├── orders.csv
    ├── order_items.csv
    ├── products.csv
    ├── inventory.csv
    ├── exceptions.csv
    └── dispatch.csv
```

---

## 15. How to Run Locally

### Step 1 – Install Python

Install Python 3.x on your computer.

### Step 2 – Clone the repository

```bash
git clone https://github.com/thathadivya-lgtm/Fulfillment-Hub.git
```

### Step 3 – Open the project folder

```bash
cd Fulfillment-Hub
```

### Step 4 – Install required packages

```bash
pip install -r requirements.txt
```

### Step 5 – Run the application

```bash
streamlit run app.py
```

The application will open in your web browser.

---

## 16. Sample Data

The repository contains sample operational data for demonstrating:

- Order fulfillment
- Inventory management
- Priority orders
- Secondary → Main stock transfer
- Picking and packing
- Staging
- Courier handoff
- Shipment
- Operational exceptions

---

## 17. Testing Performed

The prototype was tested using multiple operational scenarios:

- Normal order fulfillment
- Priority verification
- Warehouse assignment
- Main warehouse stock availability
- Secondary → Main stock transfer
- Insufficient stock exception
- Exception resolution
- Picking verification
- Packing verification
- Staging assignment
- Staging capacity exception
- Courier handoff
- Shipment confirmation
- Warehouse role permissions
- Dispatch role permissions
- Viewer permissions

---

## 18. Prototype Limitations

This is a prototype designed to demonstrate the operational workflow.

Current limitations include:

- Data is stored in CSV files.
- Shipping labels are represented by internal label references.
- No real courier API is integrated.
- Tracking numbers are demo values.
- No live warehouse management system is connected.
- The prototype does not generate physical shipping-label PDFs.

---

## 19. Future Enhancements

Possible future improvements include:

- Database integration
- Real courier API integration
- Automated notifications
- Barcode scanning
- Real shipping-label generation
- Customer communication tracking
- Detailed audit logs
- Automated SLA alerts
- Integration with warehouse management systems

---

## 20. Conclusion

Fulfillment Hub provides a structured prototype for managing e-commerce fulfillment operations.

It connects order tracking, inventory, picking, packing, staging, exceptions, and dispatch activities in one application.

The solution focuses on improving operational visibility and preventing fulfillment errors through verification and controlled workflow steps.

## Author

**Divya Thatha**

[LinkedIn](https://www.linkedin.com/in/divya-thatha/) | [GitHub](https://github.com/thathadivya-lgtm)
