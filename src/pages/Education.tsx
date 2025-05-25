import { motion } from 'framer-motion';

export default function Education() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center mb-12"
      >
        <h1 className="text-4xl font-bold text-gray-900 sm:text-5xl">
          Mortgage Education Center
        </h1>
        <p className="mt-4 text-xl text-gray-500">
          Learn everything you need to know about mortgages and make informed decisions.
        </p>
      </motion.div>

      <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
        {educationTopics.map((topic, index) => (
          <motion.div
            key={topic.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className="bg-white rounded-lg shadow-sm p-6 hover:shadow-lg transition-shadow"
          >
            <h2 className="text-xl font-semibold text-gray-900 mb-4">{topic.title}</h2>
            <p className="text-gray-600 mb-4">{topic.description}</p>
            <button className="text-purple-700 font-medium hover:text-purple-800">
              Learn more →
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

const educationTopics = [
  {
    title: 'Understanding Mortgage Types',
    description: 'Learn about different mortgage types including fixed-rate, adjustable-rate, and government-backed loans.',
  },
  {
    title: 'Interest Rates Explained',
    description: 'Discover how mortgage interest rates work, what affects them, and how to get the best rate.',
  },
  {
    title: 'Down Payments',
    description: 'Understand down payment requirements, PMI, and strategies for saving for your down payment.',
  },
  {
    title: 'The Mortgage Process',
    description: 'A step-by-step guide to the mortgage application and approval process.',
  },
  {
    title: 'Refinancing Basics',
    description: 'Learn when and why to refinance your mortgage, and how the process works.',
  },
  {
    title: 'Mortgage Terms Glossary',
    description: 'A comprehensive guide to common mortgage terms and what they mean.',
  },
];