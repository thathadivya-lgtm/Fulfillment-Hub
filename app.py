import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Fulfillment Hub", page_icon="📦", layout="wide")
DATA = Path(__file__).parent / "data"

@st.cache_data
def load_data():
    orders = pd.read_csv(DATA / "orders.csv", parse_dates=["order_date", "deadline"])
    inventory = pd.read_csv(DATA / "inventory.csv", parse_dates=["last_verified"])
    order_items = pd.read_csv(DATA / "order_items.csv")
    products = pd.read_csv(DATA / "products.csv")
    exceptions = pd.read_csv(DATA / "exceptions.csv", parse_dates=["created_at"])
    if "description" not in exceptions.columns:
        exceptions["description"] = ""
    exceptions["description"] = exceptions["description"].fillna("").astype(str)
    if "resolution" not in exceptions.columns:
        exceptions["resolution"] = ""
    exceptions["resolution"] = exceptions["resolution"].fillna("").astype(str)
    dispatch = pd.read_csv(DATA / "dispatch.csv")
    for col, default in {
        "shipping_label": "", "label_created_at": pd.NaT,
        "handoff_time": pd.NaT, "tracking_number": ""
    }.items():
        if col not in orders.columns:
            orders[col] = default
    orders["staging_location"] = orders["staging_location"].fillna("").astype(str)
    orders["shipping_label"] = orders["shipping_label"].fillna("").astype(str)
    orders["tracking_number"] = orders["tracking_number"].fillna("").astype(str)
    return orders, inventory, order_items, products, exceptions, dispatch

if "data" not in st.session_state:
    st.session_state.data = load_data()
orders, inventory, order_items, products, exceptions, dispatch = st.session_state.data

def save_state():
    orders.to_csv(DATA / "orders.csv", index=False)
    inventory.to_csv(DATA / "inventory.csv", index=False)
    order_items.to_csv(DATA / "order_items.csv", index=False)
    products.to_csv(DATA / "products.csv", index=False)
    exceptions.to_csv(DATA / "exceptions.csv", index=False)
    dispatch.to_csv(DATA / "dispatch.csv", index=False)
    st.session_state.data = (orders, inventory, order_items, products, exceptions, dispatch)
    load_data.clear()

def is_delayed(row):
    return row["status"] != "Shipped" and pd.Timestamp.now() > pd.Timestamp(row["deadline"])

def get_idx(order_id):
    x = orders.index[orders["order_id"] == order_id]
    return x[0] if len(x) else None

def get_items(order_id):
    return order_items[order_items["order_id"] == order_id].copy()

def get_inv_idx(sku, warehouse):
    x = inventory.index[(inventory["sku"] == sku) & (inventory["warehouse"] == warehouse)]
    return x[0] if len(x) else None

def add_exception(order_id, exception_type, owner, description):
    existing = exceptions[(exceptions["order_id"].astype(str) == str(order_id)) &
                          (exceptions["exception_type"] == exception_type) &
                          (exceptions["status"] == "Open")]
    if len(existing):
        return False
    exceptions.loc[len(exceptions)] = {
        "exception_id": f"EXC-{order_id}-{len(exceptions)+1:04d}",
        "order_id": order_id, "exception_type": exception_type,
        "description": description.strip(),
        "owner": owner, "status": "Open", "created_at": pd.Timestamp.now(),
        "resolution": ""
    }
    return True
def stock_check(order_id):
    row = orders[orders["order_id"] == order_id].iloc[0]
    current = True
    available = True
    main = row["warehouse"] == "Main"
    messages = []
    for _, item in get_items(order_id).iterrows():
        ii = get_inv_idx(item["sku"], row["warehouse"])
        qty = int(item["quantity"])
        if ii is None:
            current = available = False
            messages.append(f"{item['sku']}: inventory record not found.")
            continue
        avail = int(inventory.loc[ii, "available_qty"])
        verified = inventory.loc[ii, "last_verified"]
        if avail < qty:
            available = False
            messages.append(f"{item['sku']}: required {qty}, available {avail}.")
        if pd.isna(verified) or (pd.Timestamp.now() - pd.Timestamp(verified)).total_seconds() > 86400:
            current = False
            messages.append(f"{item['sku']}: physical stock verification is older than 24 hours.")
    if not main:
        messages.append("Order is assigned to Secondary. Orders ship from Main; transfer stock to Main first.")
    return current, available, main, messages

# Sidebar
st.sidebar.title("📦 Fulfillment Hub")
role = st.sidebar.selectbox("User Role", [
    "Admin / Operations Lead", "Office / Operations", "Warehouse", "Dispatch", "Viewer"
])
page = st.sidebar.radio("Navigate", [
    "Dashboard", "Order Control", "Inventory & Pick/Pack", "Dispatch", "Order History", "Exceptions"
])
st.sidebar.caption("Demo application using sample operational data.")

# Dashboard
if page == "Dashboard":
    st.title("Fulfillment Hub")
    st.subheader("Operations Control Dashboard")
    delayed_count = int(orders.apply(is_delayed, axis=1).sum())
    high_count = int((orders["priority"] == "High").sum())
    open_count = int((exceptions["status"] == "Open").sum())
    ready_count = int((orders["status"] == "Ready for Pickup").sum())
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Orders", len(orders)); c2.metric("High Priority", high_count)
    c3.metric("Open Exceptions", open_count); c4.metric("Delayed Active Orders", delayed_count)
    c5.metric("Ready for Pickup", ready_count)
    st.divider(); st.subheader("Order Status")
    status_order = ["Received", "Confirmed", "Picking", "Picked", "Packed", "Staged", "Ready for Pickup", "Handed to Courier", "Shipped"]
    counts = orders["status"].value_counts().reindex(status_order, fill_value=0).rename_axis("status").reset_index(name="orders")
    fig = px.bar(counts, x="status", y="orders", text="orders", category_orders={"status": status_order})
    fig.update_traces(textposition="outside", cliponaxis=False); fig.update_layout(height=480, margin=dict(t=35,r=20,b=100,l=20), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    delayed_active = orders[orders.apply(is_delayed, axis=1)]
    if len(delayed_active):
        delay_by_status = (delayed_active["status"].value_counts()
                           .reindex(status_order, fill_value=0)
                           .rename_axis("status")
                           .reset_index(name="delayed_orders"))
        delay_by_status = delay_by_status[delay_by_status["delayed_orders"] > 0]
        st.subheader("Delayed Active Orders by Status")
        st.dataframe(delay_by_status, use_container_width=True, hide_index=True)
    st.subheader("Orders Requiring Attention")
    attention = orders[(orders["priority"] == "High") | orders.apply(is_delayed, axis=1)][["order_id","priority","status","warehouse","courier","deadline"]].copy()
    if len(attention):
        attention["deadline"] = pd.to_datetime(attention["deadline"]).dt.strftime("%d-%b %H:%M")
        st.dataframe(attention, use_container_width=True, hide_index=True)
    else: st.success("No high-priority or delayed orders require attention.")

# Order Control
elif page == "Order Control":
    st.title("Order Control")
    c1,c2,c3 = st.columns(3)
    priority_filter = c1.selectbox("Priority", ["All","High","Normal"])
    status_filter = c2.selectbox("Status", ["All"] + sorted(orders["status"].dropna().unique().tolist()))
    search = c3.text_input("Search Order ID")
    filtered = orders.copy()
    if priority_filter != "All": filtered = filtered[filtered["priority"] == priority_filter]
    if status_filter != "All": filtered = filtered[filtered["status"] == status_filter]
    if search: filtered = filtered[filtered["order_id"].astype(str).str.contains(search, case=False, na=False)]
    filtered["delay_flag"] = filtered.apply(lambda r: "⚠ Delayed" if is_delayed(r) else "On Track", axis=1)
    st.dataframe(filtered[["order_id","priority","status","warehouse","courier","deadline","delay_flag"]].sort_values(["priority","deadline"]), use_container_width=True, hide_index=True)
    if not len(filtered): st.info("No orders match the selected filters."); st.stop()
    selected_order = st.selectbox("Select Order", filtered["order_id"].tolist(), index=None, placeholder="Choose an order")
    if selected_order is None: st.info("Select an order to view its workflow."); st.stop()
    idx = get_idx(selected_order); row = orders.loc[idx]
    st.write(f"**Status:** {row['status']} | **Priority:** {row['priority']} | **Warehouse:** {row['warehouse']} | **Courier:** {row['courier']}")
    selected_items = get_items(selected_order).merge(products[["sku","product_name","variant"]], on="sku", how="left")
    st.subheader("Order Details")
    st.dataframe(selected_items[["sku","product_name","variant","quantity"]], use_container_width=True, hide_index=True)

    if row["status"] == "Received":
        st.subheader("1. Priority & Warehouse Verification")
        if role in ["Admin / Operations Lead","Office / Operations"]:
            p_opts=["High","Normal"]; w_opts=["Main","Secondary"]
            p=st.selectbox("Verify Priority",p_opts,index=p_opts.index(row["priority"]) if row["priority"] in p_opts else 0,key=f"p_{selected_order}")
            w=st.selectbox("Assign Warehouse",w_opts,index=w_opts.index(row["warehouse"]) if row["warehouse"] in w_opts else 0,key=f"w_{selected_order}")
            if st.button("Verify Priority & Assign Warehouse",type="primary",key=f"verify_{selected_order}"):
                orders.loc[idx,"priority"]=p; orders.loc[idx,"warehouse"]=w; save_state(); st.success("Priority and warehouse verified."); st.rerun()
        else: st.info("Only Admin / Operations Lead or Office / Operations can verify priority and assign the warehouse.")
        st.subheader("2. Physical Stock Availability Check")
        current, available, main, messages = stock_check(selected_order)
        if current and available and main:
            st.success("Stock is physically verified, sufficient, and available in Main.")
            if role in ["Admin / Operations Lead","Office / Operations"] and st.button("Confirm Order & Reserve Stock",type="primary",key=f"confirm_{selected_order}"):
                c2,a2,m2,msg2=stock_check(selected_order)
                if not(c2 and a2 and m2): st.error("Stock changed. Recheck before confirmation."); [st.warning(x) for x in msg2]; st.stop()
                for _,item in selected_items.iterrows():
                    ii=get_inv_idx(item["sku"],row["warehouse"]); q=int(item["quantity"])
                    inventory.loc[ii,"reserved_qty"] += q
                    inventory.loc[ii,"available_qty"] = inventory.loc[ii,"physical_qty"]-inventory.loc[ii,"reserved_qty"]
                orders.loc[idx,"status"]="Confirmed"; save_state(); st.success("Order confirmed and stock reserved."); st.rerun()
        else:
            st.warning("Order cannot be confirmed until the stock issue is resolved.")
            for msg in messages: st.warning(msg)
            if role in ["Admin / Operations Lead","Warehouse"]:
                if not available and main:
                    transfer_plan=[]
                    transfer_possible=True
                    for _,item in selected_items.iterrows():
                        main_i=get_inv_idx(item["sku"],"Main")
                        sec_i=get_inv_idx(item["sku"],"Secondary")
                        q=int(item["quantity"])
                        if main_i is None or sec_i is None:
                            transfer_possible=False
                            break
                        main_avail=int(inventory.loc[main_i,"available_qty"])
                        sec_avail=int(inventory.loc[sec_i,"available_qty"])
                        shortage=max(0,q-main_avail)
                        if shortage > sec_avail:
                            transfer_possible=False
                            break
                        if shortage > 0:
                            transfer_plan.append((item["sku"],main_i,sec_i,shortage))
                    if transfer_possible and transfer_plan:
                        st.info("Stock is short in Main, but the required quantity is available in Secondary. Transfer the shortage to Main before confirming the order.")
                        transfer_verified=st.checkbox("I confirm the stock has been physically moved from Secondary to Main.",key=f"transfer_verify_{selected_order}")
                        if st.button("Transfer Required Stock: Secondary → Main",type="primary",key=f"transfer_order_{selected_order}"):
                            if not transfer_verified:
                                st.warning("Confirm the physical stock transfer first.")
                            else:
                                now=datetime.now().strftime("%Y-%m-%d %H:%M")
                                for sku,main_i,sec_i,qty in transfer_plan:
                                    inventory.loc[sec_i,"physical_qty"]-=qty
                                    inventory.loc[sec_i,"available_qty"]=inventory.loc[sec_i,"physical_qty"]-inventory.loc[sec_i,"reserved_qty"]
                                    inventory.loc[main_i,"physical_qty"]+=qty
                                    inventory.loc[main_i,"available_qty"]=inventory.loc[main_i,"physical_qty"]-inventory.loc[main_i,"reserved_qty"]
                                    inventory.loc[sec_i,"last_verified"]=now
                                    inventory.loc[main_i,"last_verified"]=now
                                save_state(); st.success("Stock transferred from Secondary to Main. Recheck stock before confirming the order."); st.rerun()
                if not current and st.button("Record Stock Verification Exception",key=f"old_{selected_order}"):
                    add_exception(selected_order,"Stock not physically verified","Warehouse","Physical stock has not been verified within the required freshness window."); save_state(); st.success("Exception recorded."); st.rerun()
                if not available and st.button("Record Insufficient Stock Exception",key=f"short_{selected_order}"):
                    add_exception(selected_order,"Insufficient stock","Warehouse","Required quantity is not available in the assigned warehouse."); save_state(); st.success("Exception recorded."); st.rerun()
            if not main: st.info("Transfer required: use Inventory & Pick/Pack to move available stock from Secondary to Main, then recheck.")

    elif row["status"] == "Confirmed":
        st.subheader("3. Courier Assignment & Shipping Label")
        if role in ["Admin / Operations Lead","Office / Operations"]:
            couriers=["Delhivery","Blue Dart","DTDC","Ecom Express"]
            courier=st.selectbox("Select Courier",couriers,index=couriers.index(row["courier"]) if row["courier"] in couriers else 0,key=f"courier_{selected_order}")
            if str(row["shipping_label"]).strip(): st.success(f"Shipping label: {row['shipping_label']}")
            if st.button("Assign Courier & Create Shipping Label",type="primary",key=f"label_{selected_order}"):
                orders.loc[idx,"courier"]=courier; orders.loc[idx,"shipping_label"]=f"LBL-{selected_order}"; orders.loc[idx,"label_created_at"]=datetime.now().strftime("%Y-%m-%d %H:%M"); orders.loc[idx,"status"]="Picking"; save_state(); st.success(f"{courier} assigned and label created."); st.rerun()
        else: st.info("Courier assignment and label creation are handled by Admin / Operations Lead or Office / Operations.")

    elif row["status"] == "Picking":
        st.subheader("4. Picking")
        st.write(f"Warehouse: **{row['warehouse']}** | Courier: **{row['courier']}** | Label: **{row['shipping_label']}**")
        if role in ["Admin / Operations Lead","Warehouse"]:
            verified=st.checkbox("I verified the SKU, product, variant and quantity against the pick list.",key=f"pickv_{selected_order}")
            if st.button("Confirm Picking",type="primary",key=f"pick_{selected_order}"):
                if not verified: st.warning("Complete pick verification first.")
                else:
                    ok=True; msgs=[]
                    for _,item in selected_items.iterrows():
                        ii=get_inv_idx(item["sku"],row["warehouse"]); q=int(item["quantity"])
                        if ii is None: ok=False; msgs.append(f"{item['sku']}: inventory record not found."); continue
                        ph=int(inventory.loc[ii,"physical_qty"]); res=int(inventory.loc[ii,"reserved_qty"])
                        if ph<q: ok=False; msgs.append(f"{item['sku']}: physical stock {ph}; required {q}.")
                        if res<q: ok=False; msgs.append(f"{item['sku']}: reserved stock {res}; required {q}.")
                    if not ok:
                        st.error("Picking cannot be completed."); [st.warning(x) for x in msgs]
                        if st.button("Record Picking Stock Exception",key=f"pickexc_{selected_order}"):
                            add_exception(selected_order,"Picking stock mismatch","Warehouse","Physical stock did not match the inventory record during picking."); save_state(); st.success("Exception recorded."); st.rerun()
                    else:
                        for _,item in selected_items.iterrows():
                            ii=get_inv_idx(item["sku"],row["warehouse"]); q=int(item["quantity"])
                            inventory.loc[ii,"physical_qty"]-=q; inventory.loc[ii,"reserved_qty"]-=q; inventory.loc[ii,"available_qty"]=inventory.loc[ii,"physical_qty"]-inventory.loc[ii,"reserved_qty"]
                        orders.loc[idx,"status"]="Picked"; save_state(); st.success("Picking completed and inventory updated."); st.rerun()
        else: st.info("Only Warehouse or Admin / Operations Lead can complete picking.")

    elif row["status"] == "Picked":
        st.subheader("5. Packing Verification")
        if role in ["Admin / Operations Lead","Warehouse"]:
            final_check=st.checkbox("I verified product, variant, quantity, shipping label and package seal.",key=f"final_{selected_order}")
            if st.button("Verify Packing & Mark as Packed",type="primary",key=f"pack_{selected_order}"):
                if not final_check: st.warning("Complete packing verification before marking the order as Packed.")
                else:
                    orders.loc[idx,"status"]="Packed"
                    save_state()
                    st.success("Packing verified. Order marked as Packed.")
                    st.rerun()
        else: st.info("Only Warehouse or Admin / Operations Lead can complete packing verification.")

    elif row["status"] == "Packed":
        st.subheader("6. Send to Staging")
        if role in ["Admin / Operations Lead","Warehouse"]:
            st.write("Packing verification is complete. Send the sealed order to the staging queue.")
            if st.button("Send to Staging",type="primary",key=f"stage_{selected_order}"):
                orders.loc[idx,"status"]="Staged"
                save_state()
                st.success("Order moved to Staged.")
                st.rerun()
        else: st.info("Only Warehouse or Admin / Operations Lead can send a packed order to staging.")
    else:
        st.info("This order is handled from the Dispatch page at its current stage.")

# Inventory
elif page == "Inventory & Pick/Pack":
    st.title("Inventory & Pick/Pack Control")
    inv_display=inventory.merge(products[["sku","product_name","variant"]],on="sku",how="left")[["sku","product_name","variant","warehouse","physical_qty","reserved_qty","available_qty","last_verified"]]
    st.subheader("Inventory"); st.dataframe(inv_display,use_container_width=True,hide_index=True)
    st.divider(); st.subheader("Physical Stock Verification")
    if role == "Warehouse":
        sku=st.selectbox("SKU",products["sku"].tolist(),key="verify_sku"); wh=st.selectbox("Warehouse",["Main","Secondary"],key="verify_wh"); ii=get_inv_idx(sku,wh)
        if ii is not None:
            physical=int(inventory.loc[ii,"physical_qty"]); reserved=int(inventory.loc[ii,"reserved_qty"])
            st.write(f"Recorded physical: **{physical}** | Reserved: **{reserved}**")
            new_qty=st.number_input("Physically verified quantity",min_value=0,value=physical,step=1)
            if st.button("Confirm Physical Stock",type="primary",key="physical"):
                if int(new_qty)<reserved: st.error("Physical quantity cannot be below reserved stock.")
                else:
                    inventory.loc[ii,"physical_qty"]=int(new_qty); inventory.loc[ii,"available_qty"]=int(new_qty)-reserved; inventory.loc[ii,"last_verified"]=datetime.now().strftime("%Y-%m-%d %H:%M"); save_state(); st.success("Physical stock updated."); st.rerun()
    else: st.info("Only Warehouse can update physical stock.")
    st.divider(); st.subheader("Secondary → Main Stock Transfer")
    if role in ["Admin / Operations Lead","Warehouse"]:
        st.info("Coordinate with the Warehouse team to physically move the stock before confirming this transfer in the system.")
        sku=st.selectbox("SKU to Transfer",products["sku"].tolist(),key="transfer_sku"); qty=st.number_input("Quantity to Transfer",min_value=1,value=1,step=1,key="transfer_qty")
        src=get_inv_idx(sku,"Secondary"); dst=get_inv_idx(sku,"Main")
        if src is not None and dst is not None:
            avail=int(inventory.loc[src,"available_qty"]); st.write(f"Available in Secondary: **{avail}**")
            if st.button("Confirm Warehouse Transfer to Main",type="primary",key="transfer"):
                if int(qty)>avail: st.error("Transfer quantity exceeds available Secondary stock.")
                else:
                    inventory.loc[src,"physical_qty"]-=int(qty); inventory.loc[src,"available_qty"]=inventory.loc[src,"physical_qty"]-inventory.loc[src,"reserved_qty"]
                    inventory.loc[dst,"physical_qty"]+=int(qty); inventory.loc[dst,"available_qty"]=inventory.loc[dst,"physical_qty"]-inventory.loc[dst,"reserved_qty"]
                    now=datetime.now().strftime("%Y-%m-%d %H:%M"); inventory.loc[src,"last_verified"]=now; inventory.loc[dst,"last_verified"]=now; save_state(); st.success("Warehouse transfer confirmed: stock moved from Secondary to Main."); st.rerun()
    else: st.info("Only Warehouse or Admin / Operations Lead can transfer stock.")
    st.divider(); st.subheader("Low Available Stock")
    low=inv_display[inv_display["available_qty"]<=3]
    if len(low): st.warning("Some SKUs have low available stock."); st.dataframe(low,use_container_width=True,hide_index=True)
    else: st.success("No low-stock items in the current sample data.")

# Dispatch
elif page == "Dispatch":
    st.title("Staging & Dispatch Control")
    dispatch_view=orders[orders["status"].isin(["Staged","Ready for Pickup","Handed to Courier"])][["order_id","priority","status","courier","shipping_label","staging_location"]]
    st.subheader("Staging / Pickup Queue"); st.dataframe(dispatch_view,use_container_width=True,hide_index=True)
    st.divider(); st.subheader("Assign Staging Location")
    staged=dispatch_view[dispatch_view["status"]=="Staged"]
    if len(staged):
        oid=st.selectbox("Order",staged["order_id"].tolist(),key="stage_order")
        locations=[f"A-{i:02d}" for i in range(1,9)]+[f"B-{i:02d}" for i in range(1,9)]
        occupied=orders[orders["status"].isin(["Staged","Ready for Pickup"])]["staging_location"].dropna().tolist(); available_locations=[x for x in locations if x not in occupied]
        if available_locations:
            loc=st.selectbox("Staging Location",available_locations,key=f"loc_{oid}"); verify=st.checkbox("I verified the Order ID, shipping label, courier and package seal.",key=f"stagev_{oid}")
            if role in ["Admin / Operations Lead","Warehouse"]:
                if st.button("Verify Staging & Mark Ready for Pickup",type="primary",key=f"assign_{oid}"):
                    if not verify: st.warning("Complete staging verification first.")
                    else:
                        ii=get_idx(oid); orders.loc[ii,"staging_location"]=loc; orders.loc[ii,"status"]="Ready for Pickup"; save_state(); st.success(f"{oid} assigned to {loc}."); st.rerun()
            else: st.info("Only Warehouse or Admin / Operations Lead can complete staging.")
        else:
            st.warning("No staging locations are available.")
            if role != "Viewer":
                if st.button("Record Staging Capacity Exception", type="secondary", key=f"stage_exc_{oid}"):
                    if add_exception(oid, "Staging capacity", "Warehouse", "No staging location available for this packed order."):
                        save_state(); st.success(f"Staging capacity exception recorded for {oid}."); st.rerun()
                    else:
                        st.info("An open staging capacity exception already exists for this order.")
    else: st.info("No orders are currently waiting for staging.")
    st.divider(); st.subheader("Courier Handoff")
    ready=orders[orders["status"]=="Ready for Pickup"]
    if len(ready):
        oid=st.selectbox("Order Ready for Courier",ready["order_id"].tolist(),key="handoff_order"); r=ready[ready["order_id"]==oid].iloc[0]
        st.write(f"**Courier:** {r['courier']} | **Location:** {r['staging_location']} | **Label:** {r['shipping_label']}")
        verify=st.checkbox("I verified the order, courier and package before handoff.",key=f"handoffv_{oid}")
        if role in ["Admin / Operations Lead","Dispatch"]:
            if st.button("Confirm Courier Handoff",type="primary",key=f"handoff_{oid}"):
                if not verify: st.warning("Complete courier handoff verification first.")
                elif not str(r["staging_location"]).strip(): st.error("A staging location is required.")
                else:
                    ii=get_idx(oid); orders.loc[ii,"handoff_time"]=datetime.now().strftime("%Y-%m-%d %H:%M"); orders.loc[ii,"status"]="Handed to Courier"; save_state(); st.success(f"{oid} handed to {r['courier']}."); st.rerun()
        else: st.info("Only Dispatch or Admin / Operations Lead can confirm handoff.")
    else: st.info("No orders are currently ready for pickup.")
    st.divider(); st.subheader("Confirm Shipment")
    handoff=orders[orders["status"]=="Handed to Courier"]
    if len(handoff):
        oid=st.selectbox("Order Handed to Courier",handoff["order_id"].tolist(),key="ship_order"); r=handoff[handoff["order_id"]==oid].iloc[0]
        tracking=st.text_input("Tracking Number",value=str(r["tracking_number"]),key=f"tracking_{oid}")
        if role in ["Admin / Operations Lead","Dispatch"]:
            if st.button("Mark as Shipped",type="primary",key=f"ship_{oid}"):
                if not tracking.strip(): st.warning("Enter a tracking number.")
                else:
                    ii=get_idx(oid); orders.loc[ii,"tracking_number"]=tracking.strip(); orders.loc[ii,"status"]="Shipped"; save_state(); st.success(f"{oid} marked as shipped."); st.rerun()
        else: st.info("Only Dispatch or Admin / Operations Lead can mark shipped.")
    else: st.info("No orders are currently handed to a courier.")

# Order History
elif page == "Order History":
    st.title("Order History")
    history=orders[orders["status"].isin(["Handed to Courier","Shipped"])].copy()
    if len(history):
        st.dataframe(history[["order_id","priority","warehouse","courier","shipping_label","staging_location","handoff_time","tracking_number","status","deadline"]].sort_values("deadline",ascending=False),use_container_width=True,hide_index=True)
        st.divider(); oid=st.selectbox("Select an Order",history["order_id"].tolist()); r=history[history["order_id"]==oid].iloc[0]
        st.write(f"**Order:** {r['order_id']} | **Priority:** {r['priority']} | **Warehouse:** {r['warehouse']}")
        st.write(f"**Courier:** {r['courier']} | **Status:** {r['status']} | **Tracking:** {r['tracking_number']}")
        hi=get_items(oid).merge(products[["sku","product_name","variant"]],on="sku",how="left")
        st.subheader("Order Items"); st.dataframe(hi[["sku","product_name","variant","quantity"]],use_container_width=True,hide_index=True)
    else: st.info("No completed orders yet.")

# Exceptions
elif page == "Exceptions":
    st.title("Exception Management")
    c1,c2=st.columns(2); c1.metric("Open Exceptions",int((exceptions["status"]=="Open").sum())); c2.metric("Resolved Exceptions",int((exceptions["status"]=="Resolved").sum()))
    if len(exceptions): st.dataframe(exceptions.sort_values(["status","created_at"],ascending=[True,False]),use_container_width=True,hide_index=True)
    st.divider(); st.subheader("Report an Operational Exception")
    if role != "Viewer":
        oid=st.selectbox("Order",orders["order_id"].tolist(),key="exception_order")
        etype=st.selectbox("Exception Type",["Insufficient stock","Stock not physically verified","Wrong product / variant","Wrong quantity","Misplaced package","Staging capacity","Courier / pickup issue","Picking stock mismatch","Other operational issue"],key="exception_type")
        owner={"Insufficient stock":"Warehouse","Stock not physically verified":"Warehouse","Wrong product / variant":"Warehouse","Wrong quantity":"Warehouse","Misplaced package":"Warehouse","Staging capacity":"Warehouse","Courier / pickup issue":"Dispatch","Picking stock mismatch":"Warehouse","Other operational issue":"Operations"}[etype]
        default_description={
            "Insufficient stock":"Required quantity is not available in the assigned warehouse.",
            "Stock not physically verified":"Stock has not been physically verified within the required freshness window.",
            "Wrong product / variant":"Picked product or variant does not match the order.",
            "Wrong quantity":"Picked quantity does not match the ordered quantity.",
            "Misplaced package":"Package location could not be identified in staging.",
            "Staging capacity":"No staging location is available for the order.",
            "Courier / pickup issue":"Courier pickup or handoff issue occurred.",
            "Picking stock mismatch":"Physical stock did not match the inventory record during picking.",
            "Other operational issue":"Describe the operational issue."
        }[etype]
        description=st.text_area("Description of the problem",value=default_description,key="exception_description")
        if st.button("Record Exception",type="primary",key="record_exception"):
            if not description.strip():
                st.warning("Enter a description of the problem before recording the exception.")
            elif add_exception(oid,etype,owner,description): save_state(); st.success("Exception recorded."); st.rerun()
            else: st.info("An open exception of this type already exists for this order.")
    else: st.info("Viewer can view exceptions but cannot create or resolve them.")
    st.divider(); st.subheader("Resolve an Exception")
    open_ex=exceptions[exceptions["status"]=="Open"]
    if len(open_ex):
        if role in ["Admin / Operations Lead","Office / Operations"]:
            eid=st.selectbox("Open Exception",open_ex["exception_id"].tolist(),key="resolve_exception"); resolution=st.text_input("Resolution / action taken")
            if st.button("Mark Resolved",type="primary",key="resolve_button"):
                ei=exceptions.index[exceptions["exception_id"]==eid][0]; exceptions.loc[ei,"status"]="Resolved"; exceptions.loc[ei,"resolution"]=resolution.strip() or "Resolved after verification"; save_state(); st.success(f"{eid} marked as resolved."); st.rerun()
        else: st.info("Only Admin / Operations Lead or Office / Operations can resolve exceptions.")
    else: st.success("No open exceptions.")
