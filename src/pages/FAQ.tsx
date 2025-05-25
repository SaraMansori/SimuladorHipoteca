import { motion } from 'framer-motion';

export default function FAQ() {
  const faqs = [
    {
      question: 'What is mortgage optimization?',
      answer: 'Mortgage optimization is the process of structuring your mortgage payments and terms to minimize interest costs and maximize financial benefits over the life of your loan.'
    },
    {
      question: 'How can I lower my mortgage payments?',
      answer: 'You can lower your mortgage payments by extending your loan term, refinancing at a lower interest rate, making a larger down payment, or eliminating private mortgage insurance (PMI).'
    },
    {
      question: 'Should I make extra mortgage payments?',
      answer: 'Making extra mortgage payments can help you save on interest and pay off your loan faster. However, consider your overall financial situation, including emergency savings and other investments.'
    },
    {
      question: 'What is amortization?',
      answer: 'Amortization is the gradual repayment of a mortgage loan through regular payments that cover both principal and interest. Early in the loan, most of your payment goes toward interest.'
    },
    {
      question: 'How do interest rates affect my mortgage?',
      answer: 'Interest rates directly impact your monthly payments and the total cost of your mortgage. Higher rates mean higher monthly payments and more interest paid over the life of the loan.'
    }
  ];

  return (
    <div className="max-w-3xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Frequently Asked Questions</h1>
        <div className="space-y-6">
          {faqs.map((faq, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="bg-white rounded-lg shadow-sm p-6"
            >
              <h2 className="text-xl font-semibold text-gray-900 mb-2">{faq.question}</h2>
              <p className="text-gray-600">{faq.answer}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}