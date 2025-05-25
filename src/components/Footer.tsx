import React from 'react';

export default function Footer() {
  return (
    <footer className="bg-gray-800 text-white py-6 mt-auto">
      <div className="container mx-auto px-4">
        <p className="text-center">&copy; {new Date().getFullYear()} All rights reserved.</p>
      </div>
    </footer>
  );
}