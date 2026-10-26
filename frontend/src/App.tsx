import { Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { useCart } from "./context/CartContext";
import CartBar from "./components/CartBar";
import CartDrawer from "./components/CartDrawer";
import Header from "./components/Header";
import LoginModal from "./components/LoginModal";
import Account from "./pages/Account";
import CategoryPage from "./pages/CategoryPage";
import Checkout from "./pages/Checkout";
import Home from "./pages/Home";
import InStore from "./pages/InStore";
import NotFound from "./pages/NotFound";
import OrderDetail from "./pages/OrderDetail";
import Orders from "./pages/Orders";
import ProductPage from "./pages/ProductPage";
import SearchPage from "./pages/SearchPage";
import Staff from "./pages/Staff";

export default function App() {
  const { loginOpen } = useAuth();
  const { drawerOpen } = useCart();
  return (
    <>
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/c/:slug" element={<CategoryPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/p/:id" element={<ProductPage />} />
          <Route path="/in-store" element={<InStore />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/orders/:id" element={<OrderDetail />} />
          <Route path="/account" element={<Account />} />
          <Route path="/staff" element={<Staff />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="footer">
        <span>
          smart<strong>cart</strong> · Delivery, pickup &amp; in-store shopping
        </span>
      </footer>
      <CartBar />
      {drawerOpen && <CartDrawer />}
      {loginOpen && <LoginModal />}
    </>
  );
}
