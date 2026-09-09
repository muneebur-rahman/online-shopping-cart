import os
import uuid
import pymysql
from pymysql.cursors import DictCursor
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort
)

# ==============================================================================
# DATABASE CONFIGURATION
# Update the variables below with your MySQL server credentials.
# Default root password is often empty '' or '1234' or 'root' depending on your setup.
# ==============================================================================
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '1234')  # <-- ENTER YOUR MYSQL PASSWORD HERE
DB_NAME = os.environ.get('DB_NAME', 'online_shopping_cart')
DB_PORT = int(os.environ.get('DB_PORT', 3306))

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'shopping_cart_super_secret_session_key_2026')


# ==============================================================================
# DATABASE CONNECTION HELPER
# Returns a connection with DictCursor for clean dictionary access (row['col'])
# ==============================================================================
def get_db_connection():
    """Establish and return a connection to the MySQL database."""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        cursorclass=DictCursor,
        autocommit=False
    )


def init_database_if_needed():
    """Ensure database and tables exist on application startup."""
    try:
        # First connect without specifying the DB to create it if needed
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            autocommit=True
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4;")
        cursor.execute(f"USE `{DB_NAME}`;")

        # Check if products table exists
        cursor.execute("SHOW TABLES LIKE 'products';")
        has_table = cursor.fetchone()

        if not has_table:
            # Execute database.sql to bootstrap schema & sample products
            sql_path = os.path.join(os.path.dirname(__file__), 'database.sql')
            if os.path.exists(sql_path):
                with open(sql_path, 'r', encoding='utf-8') as f:
                    statements = f.read().split(';')
                    for stmt in statements:
                        clean_stmt = stmt.strip()
                        if clean_stmt:
                            cursor.execute(clean_stmt)
                print("Database initialized successfully from database.sql.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database initialization note / warning: {e}")


# ==============================================================================
# SESSION / CART IDENTIFIER HELPER
# Ensures every visitor has a unique session ID for their isolated cart.
# ==============================================================================
@app.before_request
def ensure_session_id():
    """Assign an isolated session identifier for cart tracking if not present."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())


# ==============================================================================
# CONTEXT PROCESSOR (GLOBAL JINJA TEMPLATE HELPERS)
# Provides cart item count & total dynamically across all navbar templates.
# ==============================================================================
@app.context_processor
def inject_cart_info():
    """Inject current cart item count into every rendered template."""
    cart_count = 0
    session_id = session.get('session_id')
    if session_id:
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COALESCE(SUM(quantity), 0) AS total_items FROM cart WHERE session_id = %s",
                    (session_id,)
                )
                result = cursor.fetchone()
                if result:
                    cart_count = int(result['total_items'])
            conn.close()
        except Exception:
            cart_count = 0
    return dict(cart_count=cart_count)


# ==============================================================================
# ROUTES
# ==============================================================================

# 1. GET / - Home & Product Catalog
@app.route('/', methods=['GET'])
def index():
    """
    Display product catalog with search, category filtering, and stock indicators.
    """
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Retrieve distinct categories for navigation filter chips
            cursor.execute("SELECT DISTINCT category FROM products ORDER BY category ASC")
            categories = [row['category'] for row in cursor.fetchall()]

            # Build query with optional filters
            sql = "SELECT * FROM products WHERE 1=1"
            params = []

            if category_filter:
                sql += " AND category = %s"
                params.append(category_filter)

            if search_query:
                sql += " AND (name LIKE %s OR description LIKE %s)"
                search_param = f"%{search_query}%"
                params.extend([search_param, search_param])

            sql += " ORDER BY id ASC"
            cursor.execute(sql, tuple(params))
            products = cursor.fetchall()

        return render_template(
            'index.html',
            products=products,
            categories=categories,
            active_category=category_filter,
            search_query=search_query
        )
    finally:
        conn.close()


# 2. GET /cart - View Shopping Cart
@app.route('/cart', methods=['GET'])
def view_cart():
    """
    Display all items in the visitor's shopping cart, unit price, subtotals,
    and the calculated grand total.
    """
    session_id = session.get('session_id')
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Join cart with products to get current pricing and stock
            cursor.execute("""
                SELECT 
                    c.id AS cart_id,
                    c.product_id,
                    c.quantity,
                    p.name,
                    p.description,
                    p.price,
                    p.image,
                    p.stock,
                    p.category,
                    (p.price * c.quantity) AS subtotal
                FROM cart c
                JOIN products p ON c.product_id = p.id
                WHERE c.session_id = %s
                ORDER BY c.created_at DESC
            """, (session_id,))
            cart_items = cursor.fetchall()

            grand_total = sum(item['subtotal'] for item in cart_items)

        return render_template('cart.html', cart_items=cart_items, grand_total=grand_total)
    finally:
        conn.close()


# 3. POST /add-to-cart/<product_id> - Add Product to Cart
@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    """
    Add selected product to the cart. If already present, increment quantity.
    Validates against available warehouse inventory stock.
    """
    session_id = session.get('session_id')
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Verify product existence and stock
            cursor.execute("SELECT id, name, stock FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()

            if not product:
                flash("Product not found.", "error")
                return redirect(url_for('index'))

            if product['stock'] <= 0:
                flash(f"Sorry, '{product['name']}' is currently out of stock.", "warning")
                return redirect(request.referrer or url_for('index'))

            # Check if product is already in this session's cart
            cursor.execute(
                "SELECT id, quantity FROM cart WHERE session_id = %s AND product_id = %s",
                (session_id, product_id)
            )
            existing_cart_item = cursor.fetchone()

            if existing_cart_item:
                new_quantity = existing_cart_item['quantity'] + 1
                if new_quantity > product['stock']:
                    flash(
                        f"Cannot add more '{product['name']}'. Only {product['stock']} units available in stock.",
                        "warning"
                    )
                    return redirect(request.referrer or url_for('view_cart'))
                
                cursor.execute(
                    "UPDATE cart SET quantity = %s WHERE id = %s",
                    (new_quantity, existing_cart_item['id'])
                )
            else:
                cursor.execute(
                    "INSERT INTO cart (session_id, product_id, quantity) VALUES (%s, %s, %s)",
                    (session_id, product_id, 1)
                )

            conn.commit()
            flash(f"Added '{product['name']}' to your cart!", "success")
            return redirect(request.referrer or url_for('view_cart'))
    except Exception as e:
        conn.rollback()
        flash(f"An error occurred while adding to cart: {e}", "error")
        return redirect(url_for('index'))
    finally:
        conn.close()


# 4. POST /update-cart/<product_id> - Update Cart Quantity
@app.route('/update-cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    """
    Update item quantity in cart. Validates available stock.
    If quantity <= 0, the item is removed from the cart.
    """
    session_id = session.get('session_id')
    try:
        new_qty = int(request.form.get('quantity', 1))
    except (ValueError, TypeError):
        flash("Invalid quantity entered.", "error")
        return redirect(url_for('view_cart'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # If quantity is zero or negative, remove the item
            if new_qty <= 0:
                cursor.execute(
                    "DELETE FROM cart WHERE session_id = %s AND product_id = %s",
                    (session_id, product_id)
                )
                conn.commit()
                flash("Item removed from cart.", "info")
                return redirect(url_for('view_cart'))

            # Check stock
            cursor.execute("SELECT name, stock FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()

            if not product:
                flash("Product not found.", "error")
                return redirect(url_for('view_cart'))

            if new_qty > product['stock']:
                flash(
                    f"Requested quantity exceeds available inventory for '{product['name']}'. Max available: {product['stock']}.",
                    "warning"
                )
                return redirect(url_for('view_cart'))

            cursor.execute(
                "UPDATE cart SET quantity = %s WHERE session_id = %s AND product_id = %s",
                (new_qty, session_id, product_id)
            )
            conn.commit()
            flash("Cart updated successfully.", "success")
            return redirect(url_for('view_cart'))
    except Exception as e:
        conn.rollback()
        flash(f"Error updating cart: {e}", "error")
        return redirect(url_for('view_cart'))
    finally:
        conn.close()


# 5. GET /remove-from-cart/<product_id> - Remove Item from Cart
@app.route('/remove-from-cart/<int:product_id>', methods=['GET', 'POST'])
def remove_from_cart(product_id):
    """
    Remove the specified product from the visitor's cart.
    """
    session_id = session.get('session_id')
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM cart WHERE session_id = %s AND product_id = %s",
                (session_id, product_id)
            )
            conn.commit()
            flash("Item removed from cart.", "info")
        return redirect(url_for('view_cart'))
    except Exception as e:
        conn.rollback()
        flash(f"Error removing item: {e}", "error")
        return redirect(url_for('view_cart'))
    finally:
        conn.close()


# 6. GET & POST /checkout - Customer Information & Address
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """
    GET: Render customer details form and current order summary.
    POST: Validate shipping details, calculate final total, and proceed to payment.
    """
    session_id = session.get('session_id')
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Query cart items
            cursor.execute("""
                SELECT 
                    c.product_id,
                    c.quantity,
                    p.name,
                    p.price,
                    p.image,
                    p.stock,
                    (p.price * c.quantity) AS subtotal
                FROM cart c
                JOIN products p ON c.product_id = p.id
                WHERE c.session_id = %s
            """, (session_id,))
            cart_items = cursor.fetchall()

        if not cart_items:
            flash("Your cart is empty! Add products before checking out.", "warning")
            return redirect(url_for('view_cart'))

        total_amount = sum(item['subtotal'] for item in cart_items)

        if request.method == 'POST':
            # Extract customer inputs
            customer_name = request.form.get('customer_name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()

            # Server-side validation
            errors = []
            if not customer_name or len(customer_name) < 2:
                errors.append("Please enter your full name (at least 2 characters).")
            if not email or '@' not in email or '.' not in email:
                errors.append("Please provide a valid email address.")
            if not phone or len(phone) < 7:
                errors.append("Please enter a valid contact phone number.")
            if not address or len(address) < 5:
                errors.append("Please enter a complete shipping address.")

            if errors:
                for err in errors:
                    flash(err, "error")
                return render_template(
                    'checkout.html',
                    cart_items=cart_items,
                    total_amount=total_amount,
                    form_data=request.form
                )

            # Store validated customer info in session for payment step
            session['checkout_info'] = {
                'customer_name': customer_name,
                'email': email,
                'phone': phone,
                'address': address,
                'total_amount': float(total_amount)
            }

            return redirect(url_for('payment'))

        # GET request
        return render_template(
            'checkout.html',
            cart_items=cart_items,
            total_amount=total_amount,
            form_data=session.get('checkout_info', {})
        )
    finally:
        conn.close()


# 7. GET & POST /payment - Realistic Demo Payment Portal
@app.route('/payment', methods=['GET', 'POST'])
def payment():
    """
    GET: Display demo payment options (COD, UPI, Card) with clear demo labeling.
    POST: Process simulated payment, create order and order_items records,
          update inventory stock, clear cart, and redirect to confirmation.
    """
    session_id = session.get('session_id')
    checkout_info = session.get('checkout_info')

    # Guard: Require active checkout data
    if not checkout_info:
        flash("Please complete the checkout details first.", "warning")
        return redirect(url_for('checkout'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Re-fetch cart items to guarantee consistency
            cursor.execute("""
                SELECT 
                    c.product_id,
                    c.quantity,
                    p.name,
                    p.price,
                    p.stock,
                    (p.price * c.quantity) AS subtotal
                FROM cart c
                JOIN products p ON c.product_id = p.id
                WHERE c.session_id = %s
            """, (session_id,))
            cart_items = cursor.fetchall()

        if not cart_items:
            flash("Your cart is empty.", "warning")
            return redirect(url_for('index'))

        total_amount = sum(item['subtotal'] for item in cart_items)

        if request.method == 'POST':
            payment_method = request.form.get('payment_method', 'COD').strip()

            # Set status descriptions based on demo method
            if payment_method == 'COD':
                payment_status = 'Pending (Cash on Delivery)'
                order_status = 'Confirmed'
            elif payment_method == 'UPI':
                payment_status = 'Completed (Demo UPI)'
                order_status = 'Confirmed'
            elif payment_method == 'Card':
                payment_status = 'Completed (Demo Card)'
                order_status = 'Confirmed'
            else:
                payment_method = 'Demo Payment'
                payment_status = 'Completed'
                order_status = 'Confirmed'

            # Begin transactional order creation
            try:
                with conn.cursor() as cursor:
                    # Final stock availability check
                    for item in cart_items:
                        cursor.execute(
                            "SELECT stock, name FROM products WHERE id = %s FOR UPDATE",
                            (item['product_id'],)
                        )
                        current_prod = cursor.fetchone()
                        if current_prod['stock'] < item['quantity']:
                            conn.rollback()
                            flash(
                                f"Insufficient stock for '{current_prod['name']}'. Only {current_prod['stock']} available.",
                                "error"
                            )
                            return redirect(url_for('view_cart'))

                    # 1. Insert into orders table
                    cursor.execute("""
                        INSERT INTO orders (
                            customer_name, email, phone, address, 
                            total_amount, payment_method, payment_status, order_status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        checkout_info['customer_name'],
                        checkout_info['email'],
                        checkout_info['phone'],
                        checkout_info['address'],
                        total_amount,
                        payment_method,
                        payment_status,
                        order_status
                    ))
                    order_id = cursor.lastrowid

                    # 2. Insert order_items and decrement stock
                    for item in cart_items:
                        cursor.execute("""
                            INSERT INTO order_items (order_id, product_id, quantity, price)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            order_id,
                            item['product_id'],
                            item['quantity'],
                            item['price']
                        ))

                        cursor.execute("""
                            UPDATE products 
                            SET stock = stock - %s 
                            WHERE id = %s
                        """, (
                            item['quantity'],
                            item['product_id']
                        ))

                    # 3. Clear user's active cart
                    cursor.execute("DELETE FROM cart WHERE session_id = %s", (session_id,))

                    # Commit transaction
                    conn.commit()

                # Clean up checkout session data and remember last order ID
                session.pop('checkout_info', None)
                session['last_order_id'] = order_id

                flash("Payment processed successfully! Your order has been placed.", "success")
                return redirect(url_for('order_success', order_id=order_id))

            except Exception as e:
                conn.rollback()
                flash(f"Payment simulation failed: {e}", "error")
                return redirect(url_for('payment'))

        # GET request
        return render_template(
            'payment.html',
            checkout_info=checkout_info,
            cart_items=cart_items,
            total_amount=total_amount
        )
    finally:
        conn.close()


# 8. GET /success - Order Confirmation & Receipt
@app.route('/success', methods=['GET'])
def order_success():
    """
    Display confirmation and invoice details for the placed order.
    """
    order_id = request.args.get('order_id', type=int) or session.get('last_order_id')
    if not order_id:
        flash("No recent order found.", "info")
        return redirect(url_for('index'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Fetch order record
            cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            order = cursor.fetchone()

            if not order:
                flash("Order not found.", "error")
                return redirect(url_for('index'))

            # Fetch order line items with product details
            cursor.execute("""
                SELECT 
                    oi.quantity,
                    oi.price,
                    (oi.quantity * oi.price) AS subtotal,
                    p.name,
                    p.image,
                    p.category
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """, (order_id,))
            order_items = cursor.fetchall()

        return render_template('success.html', order=order, order_items=order_items)
    finally:
        conn.close()


# 9. GET /orders - Previous Orders Dashboard
@app.route('/orders', methods=['GET'])
def orders_history():
    """
    Display list of all customer orders, status, date, line items, and grand totals.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Fetch orders in reverse chronological order
            cursor.execute("SELECT * FROM orders ORDER BY created_at DESC, id DESC")
            orders = cursor.fetchall()

            # For each order, fetch items summary
            for order in orders:
                cursor.execute("""
                    SELECT 
                        oi.quantity,
                        oi.price,
                        p.name,
                        p.image,
                        p.category
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = %s
                """, (order['id'],))
                order['items_list'] = cursor.fetchall()

        return render_template('orders.html', orders=orders)
    finally:
        conn.close()


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
if __name__ == '__main__':
    # Initialize database tables and sample data if needed
    init_database_if_needed()
    print(" * Running ShopCart application on http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
